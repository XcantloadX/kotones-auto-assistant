set dotenv-load
set windows-shell := ["powershell", "-c"]
set shell := ["pwsh", "-c"]

shebang_pwsh := if os() == 'windows' {
  'powershell.exe'
} else {
  '/usr/bin/env pwsh'
}
shebang_python := if os() == 'windows' {
  'python.exe'
} else {
  '/usr/bin/env python'
}

default:
    @just --list

fetch-submodule:
    git submodule update --init --remote --recursive --progress --depth 1

resource:
    python tools/make_resources.py

devtool:
    cd kotonebot-devtool; npm run dev

# Check and create virtual environment
env: fetch-submodule
    #!{{shebang_pwsh}}
    Write-Host "Installing requirements..."
    $IsWindows = $env:OS -match "Windows"
    
    if ($IsWindows) {
        ./.venv/Scripts/pip install -r requirements.dev.txt
        ./.venv/Scripts/pip install -r requirements.win.txt
        ./.venv/Scripts/pip install -r ./submodules/GkmasObjectManager/requirements.txt
    } else {
        ./.venv/bin/pip install -r requirements.dev.txt
        ./.venv/bin/pip install -r ./submodules/GkmasObjectManager/requirements.txt
    }
    python tools/make_resources.py

generate-metadata: env
    #!{{shebang_python}}
    # 更新日志
    from pathlib import Path
    with open("WHATS_NEW.md", "r", encoding="utf-8") as f:
        content = f.read()
    metadata_path = Path("kaa/metadata.py")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write(f'WHATS_NEW = """\n{content}\n"""')
    
    # 版本号
    from subprocess import check_output
    # 获取当前分支上 kaa 开头的 tag，多重排序：commit 日期倒序 -> tag 日期倒序 -> tag 名称倒序
    version = check_output(['git', 'for-each-ref', '--sort=-committerdate', '--sort=-creatordate', '--sort=-refname', '--format=%(refname:short)', 'refs/tags/kaa-*', '--merged', 'HEAD']).decode().strip().split('\n')[0]
    if version.startswith('kaa-v'):
        version = version[5:]
    with open("version", "w", encoding="utf-8") as f:
        f.write(version)

extract-game-data:
    #!{{shebang_pwsh}}
    Write-Host "Extracting game data..."
    
    New-Item -ItemType File -Force -Path ./kaa/resources/__init__.py
    
    $currentHash = git -C ./submodules/gakumasu-diff rev-parse HEAD
    $hashFile = "./kaa/resources/game_ver.txt"
    $shouldUpdate = $true
    
    if (Test-Path $hashFile) {
        $savedHash = Get-Content $hashFile

        if ($currentHash -eq $savedHash) {
            Write-Host "Game data is up to date. Skipping extraction."
            $shouldUpdate = $false
        }
    }
    
    if ($shouldUpdate) {
        Write-Host "Game data needs update. Extracting..."

        $currentHash | Out-File -FilePath $hashFile
        Remove-Item ./kaa/resources/game.db
        python ./tools/db/extract_schema.py -i ./submodules/gakumasu-diff -d ./kaa/resources/game.db
        python ./tools/db/extract_resources.py
    }

@package-resource:
    Write-Host "Packaging kotonebot-resource..."
    @python -m build -s kotonebot-resource

# Package KAA
@package: env package-resource generate-metadata extract-game-data
    python tools/make_resources.py -p # Make R.py in production mode

    Write-Host "Removing old build files..."
    if (Test-Path dist) { rm -r -fo dist }
    if (Test-Path build) { rm -r -fo build }
    Write-Host "Packaging KAA..."
    @python -m build
    
    Write-Host "Copying kotonebot-resource to dist..."
    Copy-Item ./kotonebot-resource/dist/* ./dist/

    python tools/make_resources.py # Make R.py in development mode

# Upload to PyPI
publish: package
    # if (git diff-index --quiet HEAD) { } else { Write-Host "Error: Commit all changes before publishing"; exit 1 }
    @Write-Host "Uploading to PyPI..."
    twine upload dist/* -u __token__ -p $env:PYPI_TOKEN

# Upload to PyPI-Test
publish-test: package
    @Write-Host "Uploading to PyPI-Test..."
    twine upload --repository testpypi dist/* -u __token__ -p $env:PYPI_TEST_TOKEN

# 
build-bootstrap:
    #!{{shebang_pwsh}}
    echo "Building bootstrap..."
    # 构建 Python
    cd bootstrap
    python -m zipapp kaa-bootstrap
    mv kaa-bootstrap.pyz ../dist/bootstrap.pyz -fo
    
    # 构建 C++
    $msbuild = &"${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -prerelease -products * -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe
    if ($msbuild) {
        & $msbuild kaa-wrapper/kaa-wrapper.sln /p:Configuration=Release
        mv kaa-wrapper/x64/Release/kaa-wrapper.exe ../dist/kaa.exe -fo
    } else {
        Write-Host "MSBuild not found. Please install Visual Studio or build kaa-wrapper manually."
    }

# Build kaa and bootstrap
build: package build-bootstrap
