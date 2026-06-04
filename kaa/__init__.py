from pkgutil import extend_path

# Allow split package layout so external distribution (ksaa-res) can provide
# subpackages like kaa.res under the same top-level package name.
__path__ = extend_path(__path__, __name__)
