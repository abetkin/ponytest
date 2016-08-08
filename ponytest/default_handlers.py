from .utils import with_cli_args
from .config import fixture_handlers
import click

def cli_handler(key, providers):
    formatted_key =  key.replace('_', '-')
    option = ''.join(('--', formatted_key))
    no_option = '-'.join(('--no', formatted_key))
    if len(providers) == 1:
        @with_cli_args
        @click.option(option, 'enabled', is_flag=True)
        @click.option(no_option, 'disabled', is_flag=True)
        def single_provider(enabled, disabled):
            if disabled:
                return ()
            provider_key = next(p for p in providers)
            if enabled:
                return (provider_key,)
            provider = providers[provider_key]
            if getattr(provider, 'enabled', True):
                return (provider_key,)
            return ()
        return single_provider()

    @with_cli_args
    @click.option(option, 'included', multiple=True)
    @click.option(no_option, 'excluded', multiple=True)
    def multiple_providers(included, excluded, providers=providers):
        providers = {k: v for k, v in providers.items()
                    if not included or k in included
                    if not excluded or k not in excluded}
        if included or excluded:
            return providers
        return (key for key, p in providers.items()
                if getattr(p, 'enabled', True))

    return multiple_providers()


fixture_handlers['__default__'] = cli_handler