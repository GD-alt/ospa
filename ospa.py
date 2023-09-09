import logging
import os
import subprocess
from pathlib import Path
import sys
import zipfile
import time
import datetime
from traceback import format_exc as fe
from textwrap import indent

logging.disable(logging.CRITICAL)

try:
    import rich
    from rich.console import Console

    c = Console()
except ModuleNotFoundError:
    print('rich not found, attempting to install…\n')
    subprocess.Popen(["pip", "install", "rich"])
    from rich.console import Console

    c = Console()
    c.print('[green]rich installed![/green]\n')

from rich.live import Live

try:
    import sanic
except ModuleNotFoundError:
    c.print('[grey italic]sanic not found, attempting to install…[/grey italic]')
    subprocess.Popen(["pip", "install", "sanic"])
    c.print('[green]sanic installed![/green]\n')
    import sanic

import sanic.response
from sanic.request import Request
import sanic.exceptions
from sanic import Sanic

try:
    import requests
except ModuleNotFoundError:
    c.print('[grey italic]requests not found, attempting to install…[/grey italic]')
    subprocess.Popen(["pip", "install", "requests"])
    import requests

    c.print('[green]requests installed![/green]\n')

try:
    import jinja2
except ModuleNotFoundError:
    c.print('[grey italic]jinja2 not found, attempting to install…[/grey italic]')
    subprocess.Popen(["pip", "install", "jinja2"])
    import jinja2

    c.print('[green]jinja2 installed![/green]\n')

try:
    import yaml
except ModuleNotFoundError:
    c.print('[grey italic]yaml not found, attempting to install…[/grey italic]')
    subprocess.Popen(["pip", "install", "pyyaml"])
    import yaml

    c.print('[green]yaml installed![/green]\n')

avaliable_args = {
    'port': (('-p', '--port'), int),
    'php-path': (('-pp', '--php-path'), str),
    'config-path': (('-c', '--config-path'), str),
    'index': (('-i', '--index'), str),
    'log-requests': (('-l', '--log'), bool),
}

default_values = {
    'port': 12521,
    'php-path': 'php/php.exe',
    'config-path': 'config.yaml',
    'index': 'index.html',
    'log-requests': False,
}

run_args = {
    'port': None,
    'php-path': None,
    'config-path': None,
    'index': None,
    'log-requests': None,
}

args = sys.argv[1:]
args_dict = {}

if_value = False
prev_key = None
for arg in args:
    if arg.startswith('--'):
        key = arg[2:]
        args_dict[key] = True
        if_value = True
        prev_key = key

    elif arg.startswith('-'):
        key = arg[1:]
        args_dict[key] = True
        if_value = True
        prev_key = key

    elif if_value:
        if arg.startswith('-'):
            args_dict[prev_key] = True
            prev_key = None
            if_value = False

            if arg.startswith('--'):
                key = arg[2:]
                args_dict[key] = True
                if_value = True
                prev_key = key

            else:
                key = arg[1:]
                args_dict[key] = True
                if_value = True
                prev_key = key
            continue

        args_dict[prev_key] = arg
        if_value = False
        prev_key = None

    else:
        raise ValueError(f'Invalid argument: {arg}')

avaliable_args_list = [value[0][0].strip('-') for value in avaliable_args.values()]
avaliable_args_list.extend([value[0][1].strip('-') for value in avaliable_args.values()])

backwards_args_dict = {}
for key, value in avaliable_args.items():
    for arg in value[0]:
        backwards_args_dict[arg.strip('-')] = key

for key, value in args_dict.items():
    if key not in avaliable_args_list:
        raise ValueError(f'Invalid argument: {key}')

    if key in backwards_args_dict:
        run_args[backwards_args_dict[key]] = value


def on_request(request: Request):
    if not run_args['log-requests']:
        return

    if request.method == 'POST':
        method = '[green bold]POST[/green bold]'
    elif request.method == 'GET':
        method = '[blue bold]GET[/blue bold]'
    elif request.method == 'PUT':
        method = '[yellow bold]PUT[/yellow bold]'
    elif request.method == 'DELETE':
        method = '[red bold]DELETE[/red bold]'
    elif request.method == 'PATCH':
        method = '[magenta bold]PATCH[/magenta bold]'
    elif request.method == 'HEAD':
        method = '[cyan bold]HEAD[/cyan bold]'
    elif request.method == 'OPTIONS':
        method = '[dark_khaki bold]OPTIONS[/dark_khaki bold]'
    else:
        method = f'[bright_black bold]{request.method}[/bright_black bold]'

    c.print(f'[bright_black italic]{datetime.datetime.strftime(datetime.datetime.now(), "%H:%M:%S")}'
            f'[/bright_black italic] {method} {request.url}')


def show_error(error: str = None, spec: str = None):
    if not spec:
        c.print(f'  [red bold]Error:[/red bold] {error}')
        return

    if spec == 'php':
        c.print(f'  [red bold]Error:[/red bold] [purple]PHP[/purple] parsing error')
    elif spec == '404':
        c.print(f'  [red bold]Error:[/red bold] [red3]404 Not Found[/red3]')
    elif spec == 'index-empty':
        c.print(f'  [red bold]Error:[/red bold] [italic]index[/italic] file not found')
    elif spec == 'no-resource':
        c.print(f'  [red bold]Error:[/red bold] there\'s no such resource')
    elif spec == '500':
        c.print(f'  [red bold]Error:[/red bold] [red3]500 Internal Server Error[/red3]\n{indent(fe(), "    ")}')
    else:
        c.print(f'  [yellow bold]Warning:[/yellow bold] unknown error: {spec}')


if not run_args['config-path']:
    run_args['config-path'] = 'config.yaml'

if not Path(run_args['config-path']).exists():
    c.print(f'[yellow]Config file not found on {run_args["config-path"] or default_values["config-path"]}'
            f', creating…[/yellow]')

    for key, value in run_args.items():
        if value is None:
            run_args[key] = default_values[key]

    Path(run_args['config-path']).write_text(yaml.dump(run_args))

    c.print(f'[green]Config file created![/green]\n')

else:
    run_args_live = yaml.load(Path(run_args['config-path']).read_text(), Loader=yaml.FullLoader)
    for key, value in run_args_live.items():
        if key in run_args and run_args[key] is None:
            run_args[key] = value

php_path = run_args['php-path']
if not Path(php_path).exists():
    if not (c.input(f'[yellow]PHP not found on {run_args["php-path"]}\nAttempt an installation?[/yellow] '
                    f'(Y/N) ').lower() in ('y', 'yes')):
        c.print('[red]PHP not found, exiting…[/red]')
        exit(1)
    else:
        php_path = Path(php_path)
        php_path.parent.mkdir(exist_ok=True)

        r = requests.get('https://windows.php.net/downloads/releases/php-8.2.10-nts-Win32-vs16-x64.zip',
                         stream=True)

        with open('php.zip', 'wb') as f:
            total_length = int(r.headers.get('content-length'))
            start_time = time.perf_counter()

            with Live(None, refresh_per_second=10) as live:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        done = int(50 * f.tell() / total_length)
                        live.update(
                            f'\n[bright_black]Downloading PHP…[/bright_black] [green]{"█" * done}[/green]'
                            f'[bright_black]{"░" * (50 - done)}[/bright_black] '
                            f'[deep_sky_blue3]{round(f.tell() / 1024 / 1024, 2)}/'
                            f'{round(total_length / 1024 / 1024, 2)}[/deep_sky_blue3]'
                            f' MB (running for [deep_sky_blue3]{round(time.perf_counter() - start_time, 1)}'
                            f'[/deep_sky_blue3]s)\n'
                        )

                live.update('\n[bright_black]Extracting PHP…[/bright_black]\n')

                with zipfile.ZipFile('php.zip', 'r') as zip_ref:
                    zip_ref.extractall(php_path.parent)

                live.update('\n[bright_black]Extracting PHP[/bright_black] [green bold]done![/green bold]\n')
                time.sleep(3)
                live.update(f'\n[green bold]PHP installed![/green bold]\n'
                            f'[bright_black]php.zip now can be safely removed manually.[/bright_black]\n')

app = Sanic(__name__)
app.on_request(on_request)


@app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
async def index(request: Request):
    path = run_args['index']
    try:
        text = Path(path).read_text()
    except FileNotFoundError:
        show_error(None, 'index-empty')
        return sanic.response.text('Index file not found. Change run configuration to present file.', status=404)

    if path.endswith('.jinja2.php') or path.endswith('.j2.php'):
        myargs = request.args
        for k, value in myargs.items():
            myargs[k] = value[0]
        template = jinja2.Template(text)
        res = template.render(myargs)
        with open(f'{path.split(".")[-3]}.php', 'w') as file:
            file.write(res)
        res = subprocess.run([php_path, f'{path.split(".")[-3]}.php'], capture_output=True).stdout.decode('utf-8')
        os.remove(f'{path.split(".")[-3]}.php')
        return sanic.response.html(res)

    elif run_args['index'].endswith('.php'):
        res = subprocess.run([php_path, run_args['index']], capture_output=True).stdout.decode('utf-8')
        return sanic.response.html(res)

    elif run_args['index'].endswith('.html') or run_args['index'].endswith('htm'):
        return sanic.response.html(text)

    elif run_args['index'].endswith('.jinja2') or run_args['index'].endswith('.j2'):
        myargs = request.args
        template = jinja2.Template(text)
        return sanic.response.html(template.render(myargs))

    else:
        show_error(None, 'index-empty')
        return sanic.response.text('Expected index file to be .php or .html', status=500)


@app.get('/assets/<path>')
async def assets(request: Request, path: str):
    if path.endswith('.css'):
        loc_path = Path(f'assets/css/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text(), content_type='text/css')

    elif path.endswith('.js'):
        loc_path = Path(f'assets/js/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text(), content_type='text/javascript')

    elif path.split('.')[-1] in ('png', 'jpg', 'jpeg', 'gif', 'ico'):
        loc_path = Path(f'assets/img/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.file(loc_path)

    elif path.split('.')[-1] in ('ttf', 'woff', 'woff2'):
        loc_path = Path(f'assets/fonts/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.file(loc_path)

    else:
        loc_path = Path(f'assets/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text(), content_type='text/plain')


@app.route('/<path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
async def resource(request: Request, path: str):
    try:
        text = Path(path).read_text()
    except FileNotFoundError:
        show_error(None, '404')
        return sanic.response.text('404 Not Found', status=404)

    if path.endswith('.jinja2.php') or path.endswith('.j2.php'):
        myargs = request.args
        for k, value in myargs.items():
            myargs[k] = value[0]
        template = jinja2.Template(text)
        res = template.render(myargs)
        with open(f'{path.split(".")[-3]}.php', 'w') as file:
            file.write(res)
        res = subprocess.run([php_path, f'{path.split(".")[-3]}.php'], capture_output=True).stdout.decode('utf-8')
        os.remove(f'{path.split(".")[-3]}.php')
        return sanic.response.html(res)

    elif path.endswith('.php'):
        res = subprocess.run([php_path, path], capture_output=True).stdout.decode('utf-8')
        return sanic.response.html(res)

    elif path.endswith('.html') or path.endswith('htm'):
        return sanic.response.html(text)

    elif path.endswith('.jinja2') or path.endswith('.j2'):
        myargs = request.args
        for k, value in myargs.items():
            myargs[k] = value[0]
        template = jinja2.Template(text)
        return sanic.response.html(template.render(myargs))

    else:
        return sanic.response.text(text)


@app.exception(sanic.exceptions.NotFound)
async def not_found(request: Request, exception: sanic.exceptions.NotFound):
    show_error(None, '404')
    return sanic.response.text('404 Not Found', status=404)


# Any other exception
@app.exception(Exception)
async def server_error(request: Request, exception: Exception):
    show_error(None, '500')
    return sanic.response.text('500 Internal Server Error', status=500)


if __name__ == '__main__':
    c.print(f'[green bold]Server started![/green bold]\nAccess it on http://localhost:{run_args["port"]}\n')
    app.run(host='localhost', port=run_args['port'], debug=False)
    c.print(f'[red bold]Server stopped![/red bold]')
