import json
import os
import sys
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import click

from kaa.main.kaa import Kaa
from kotonebot.backend.context import tasks_from_id, task_registry
from kaa.config import manager as config_manager


@dataclass
class CliTaskConfig:
    before_invoke: Callable[[], None] | None = None
    kwargs_transform: Callable[[dict], dict] | None = None


_task_configs: dict[str, CliTaskConfig] = {}


def configure(task_configs: dict[str, CliTaskConfig]) -> None:
    _task_configs.update(task_configs)


def cli_root_dir() -> str:
    if not os.path.basename(sys.executable).startswith('python'):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def make_kaa(config: str | None, allow_multi_profile: bool = False) -> Kaa:
    if config is None:
        profiles = config_manager.list_profiles()
        if len(profiles) > 1 and not allow_multi_profile:
            names = ', '.join(profiles)
            raise click.UsageError(
                f'Multiple profiles found ({names}). Please specify one with -c/--config.'
            )
    return Kaa(profile_name=config)


@click.group(invoke_without_command=True)
@click.option('-c', '--config', default=None, help='Configuration profile name to use')
@click.option('-lp', '--log-path', default=None, help='Path to the log file. Does not log to file if not specified.')
@click.option('-ll', '--log-level', default='DEBUG', help='Log level. Default: DEBUG')
@click.option('--kill-dmm', is_flag=True, default=False, help='Kill DMM Game Player when tasks are completed.')
@click.option('--kill-game', is_flag=True, default=False, help='Kill gakumas.exe when tasks are completed.')
@click.version_option(package_name='ksaa', prog_name='kaa')
@click.pass_context
def cli(ctx: click.Context, config: str | None, log_path: str | None, log_level: str, kill_dmm: bool, kill_game: bool) -> None:
    """Command-line interface for Kotone's Auto Assistant"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = config
    ctx.obj['log_path'] = log_path
    ctx.obj['log_level'] = log_level
    ctx.obj['kill_dmm'] = kill_dmm
    ctx.obj['kill_game'] = kill_game

    if ctx.invoked_subcommand is None:
        log_filename = datetime.now().strftime('logs/%y-%m-%d-%H-%M-%S.log')
        from kaa.util.logging import setup, add_file_logger
        setup()
        add_file_logger(log_filename)

        # Always use debug level
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)

        from kaa.main.qml_app import main as qml_main
        qml_main()


@cli.group()
def task() -> None:
    """Task related commands"""


@task.command()
@click.argument('task_ids', nargs=-1)
@click.option('--kwargs', 'raw_kwargs', default=None, help='Task kwargs as JSON string')
@click.pass_context
def invoke(ctx: click.Context, task_ids: tuple[str, ...], raw_kwargs: str | None) -> None:
    """Invoke a task or many tasks"""
    task_ids_list = list(task_ids)
    if not task_ids_list:
        raise click.UsageError('No tasks specified.')

    unknown = [t for t in task_ids_list if t != '*' and t not in task_registry]
    if unknown:
        available = ', '.join(task_registry.keys())
        raise click.UsageError(
            f'Unknown task id(s): {", ".join(unknown)}. Available: {available}'
        )

    kaa = make_kaa(ctx.obj['config'])
    log_level = getattr(logging, ctx.obj['log_level'], None)
    if log_level is None:
        raise click.UsageError(f'Invalid log level: {ctx.obj["log_level"]}')
    kaa.set_log_level(log_level)
    from kaa.util.logging import add_file_logger
    if ctx.obj['log_path'] is not None:
        add_file_logger(ctx.obj['log_path'])

    kwargs = json.loads(raw_kwargs) if raw_kwargs else None

    if '*' in task_ids_list:
        if len(task_ids_list) > 1:
            raise click.UsageError('Cannot specify other tasks when using wildcard.')
        kaa.run_all()
    else:
        for task_id in task_ids_list:
            task_cfg = _task_configs.get(task_id)
            if task_cfg and task_cfg.before_invoke:
                task_cfg.before_invoke()
            task_kwargs = kwargs
            if task_cfg and task_cfg.kwargs_transform and task_kwargs is not None:
                task_kwargs = task_cfg.kwargs_transform(task_kwargs)
        kaa.run(tasks_from_id(task_ids_list))

    if ctx.obj['kill_dmm']:
        os.system('taskkill /f /im DMMGamePlayer.exe')
    if ctx.obj['kill_game']:
        os.system('taskkill /f /im gakumas.exe')


@task.command(name='list')
@click.pass_context
def task_list(ctx: click.Context) -> None:
    """List all available tasks"""
    make_kaa(ctx.obj['config'])  # 确保任务已加载

    if not task_registry:
        click.echo('No tasks available.')
        return

    click.echo('Available tasks:')
    for t in task_registry.values():
        click.echo(f'  * {t.id}: {t.name}\n    {t.description.strip()}')


def main() -> None:
    click.echo(f'Arguments: {sys.argv}')
    cli()


if __name__ == '__main__':
    main()
