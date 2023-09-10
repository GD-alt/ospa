import logging
import os
import subprocess
from pathlib import Path
import zipfile
import time
import datetime
from traceback import format_exc as fe
from textwrap import indent
from chardet import detect
import sys

inject_js = """async function refresh() {
    // Get current path
    let path = window.location.href;

    // Find all links to styles in current HTML
    const links = document.querySelectorAll('link[rel="stylesheet"]');

    // Get current HTML contents via `fetch`
    const options = {
        method: 'GET'
    };

    // Get current params
    const params = new URLSearchParams(window.location.search);

    // Update params with `AUTOREFRESH` param
    params.set('AUTOREFRESH', 'true');
    path = path.split('?')[0];
    path = path + '?' + params.toString();

    // Get all stylesheets
    let stylesheets = [];
    for (let i = 0; i < links.length; i++) {
        const link = links[i];
        // Do `fetch` to stylesheet, get CSS to `css`
        const css = await (await fetch(link.href, options)).text();
        stylesheets.push(css);
    }

    // Get all scripts
    let scripts = [];
    for (let i = 0; i < links.length; i++) {
        const link = links[i];
        // Do `fetch` to `scripts`, get JS to `script` if there's a `src` attribute and name doesn't contain `refresh.js`
        if (link.src && !link.src.includes('refresh.js')) {
            const script = await (await fetch(link.src, options)).text();
            scripts.push(script);
        }
    }

    let html = await (await fetch(path, options)).text();

    while (true) {
        // Do `fetch` to myself, get HTML to `response`

        const response = await (await fetch(path, options)).text();

        // Compare it with current HTML
        if (html !== response) {
            // If not equal, update current HTML
            document.documentElement.innerHTML = response;
            html = response;
            continue;
        }

        // Find all links to styles in current HTML
        const links = document.querySelectorAll('link[rel="stylesheet"]');
        // Get all stylesheets
        let stylesheetsNew = [];
        for (let i = 0; i < links.length; i++) {
            const link = links[i];
            // Do `fetch` to stylesheet, get CSS to `css`
            const css = await (await fetch(link.href, options)).text();
            stylesheetsNew.push(css);
        }

        // Compare it with current stylesheets
        if (stylesheetsNew.length !== stylesheets.length) {
            // If not equal, update current HTML
            document.documentElement.innerHTML = response;
            stylesheets = stylesheetsNew;
            continue;
        }

        // Recheck
        for (let i = 0; i < stylesheetsNew.length; i++) {
            const stylesheet = stylesheetsNew[i];
            // DEBUG
            console.log(stylesheet);
            console.log(stylesheets[i]);
            console.log(stylesheets[i] !== stylesheet);
            if (stylesheets[i] !== stylesheet) {
                // If not equal, update current HTML
                document.documentElement.innerHTML = response;
                stylesheets = stylesheetsNew;
            }
        }

        // Find all links to scripts in current HTML
        const scriptsLinks = document.querySelectorAll('script[src]');
        // Get all scripts
        let scriptsNew = [];
        for (let i = 0; i < scriptsLinks.length; i++) {
            const link = scriptsLinks[i];
            // Do `fetch` to `scripts`, get JS to `script` if there's a `src` attribute and name doesn't contain `refresh.js`
            if (link.src && !link.src.includes('refresh.js')) {
                const script = await (await fetch(link.src, options)).text();
                scriptsNew.push(script);
            }
        }

        // Compare it with current scripts
        if (scriptsNew.length !== scripts.length) {
            // If not equal, update current HTML
            document.documentElement.innerHTML = response;
            scripts = scriptsNew;
            continue;
        }

        // Recheck
        for (let i = 0; i < scriptsNew.length; i++) {
            const script = scriptsNew[i];
            if (scripts[i] !== script) {
                // If not equal, update current HTML
                document.documentElement.innerHTML = response;
                scripts = scriptsNew;
            }
        }
    }
}

window.onload = refresh;"""

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

avaliable_args = {
    'port': (('-p', '--port'), int),
    'php-path': (('-pp', '--php-path'), str),
    'config-path': (('-c', '--config-path'), str),
    'index': (('-i', '--index'), str),
    'log-requests': (('-l', '--log'), bool),
    'auto-refresh': (('-r', '--refresh'), bool),
    'no-php': (('-np', '--no-php'), bool),
    'no-j2':  (('-nj', '--no-j2'), bool),
}

default_values = {
    'port': 12521,
    'php-path': 'php/php.exe',
    'config-path': 'config.yaml',
    'index': 'index.html',
    'log-requests': False,
    'auto-refresh': False,
    'no-php': False,
    'no-j2': False,
}

run_args = {
    'port': None,
    'php-path': None,
    'config-path': None,
    'index': None,
    'log-requests': None,
    'auto-refresh': None,
    'no-php': None,
    'no-j2': None,
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

if not run_args['no-j2']:
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


def on_request(request: Request):
    if not run_args['log-requests']:
        return

    if 'AUTOREFRESH' in request.args and request.args['AUTOREFRESH'] == ['true']:
        return

    if '/assets/' in request.url:
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
        c.print(f'  [red bold]Error:[/red bold] [orchid bold]PHP[/orchid bold] parsing error: {error}')
    elif spec == '404':
        c.print(f'  [red bold]Error:[/red bold] [red3]404 Not Found[/red3]')
    elif spec == 'index-empty':
        c.print(f'  [red bold]Error:[/red bold] [italic]index[/italic] file not found')
    elif spec == 'index-incorrect-format':
        c.print(f'  [red bold]Error:[/red bold] [italic]index[/italic] file has incorrect format')
    elif spec == 'no-resource':
        c.print(f'  [red bold]Error:[/red bold] there\'s no such resource')
    elif spec == '500':
        c.print(f'  [red bold]Error:[/red bold] [red3]500 Internal Server Error[/red3]\n{indent(fe(), "    ")}')
    elif spec == 'encoding?':
        c.print(f'  [indian_red italic]PHP compiled with unknown encoding![/indian_red italic]')
    elif spec == 'php-off':
        c.print(f'  [dark_orange bold]Alert:[/dark_orange bold] PHP is turned off, I can\'t serve PHP files')
    elif spec == 'j2-off':
        c.print(f'  [dark_orange bold]Alert:[/dark_orange bold] Jinja2 is turned off, I can\'t serve Jinja2 files')
    else:
        c.print(f'  [yellow bold]Warning:[/yellow bold] unknown error: {spec}')


def compile_php(filename: str, debug: False) -> str:
    """
    Compiles PHP data to HTML data
    :param filename: PHP data
    :param debug: debug mode
    :return: HTML data
    """
    if not Path(filename).exists():
        raise FileNotFoundError(f'File {filename} not found')

    if not filename.endswith('.php'):
        raise ValueError(f'File {filename} is not a PHP file')

    res_bytes = subprocess.run([php_path, filename], capture_output=True).stdout

    try:
        res = res_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            res = res_bytes.decode(detect(res_bytes)['encoding'])
        except UnicodeDecodeError:
            show_error(None, 'encoding?')
            raise Exception('PHP compiled with unknown encoding!')

    if res.startswith('\nParse error') and debug:
        show_error(res.removeprefix('\nParse error: '), 'php')
        raise Exception('PHP parsing error')

    return res


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
    run_args_live = yaml.load(Path(run_args['config-path']).read_text('utf-8'), Loader=yaml.FullLoader)
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
        try:
            import requests
        except ModuleNotFoundError:
            c.print('[grey italic]requests not found, attempting to install…[/grey italic]')
            subprocess.Popen(["pip", "install", "requests"])
            import requests

            c.print('[green]requests installed![/green]\n')

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

if run_args['auto-refresh']:
    refresh_script_path = Path('assets/js/refresh.js')
    if not refresh_script_path.exists():
        if c.input(f'[yellow]Refresh script not found on {refresh_script_path}\nCreate?[/yellow] (Y/N) ').lower() \
                in ('y', 'yes'):
            refresh_script_path.parent.mkdir(exist_ok=True)
            refresh_script_path.write_text(inject_js)
            c.print('[green]Refresh script created![/green]\n')
        else:
            c.print('[red]Refresh script not found, turning refresh off.[/red]')
            run_args['auto-refresh'] = False

app = Sanic(__name__)
app.on_request(on_request)


@app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
async def index(request: Request):
    if 'AUTOREFRESH' in request.args and request.args['AUTOREFRESH'] == ['true']:
        debug = False
    else:
        debug = True

    path = run_args['index']
    try:
        text = Path(path).read_text('utf-8')
    except FileNotFoundError:
        show_error(None, 'index-empty')
        return sanic.response.text('Index file not found. Change run configuration to present file.', status=404)

    if path.endswith('.jinja2.php') or path.endswith('.j2.php'):
        if run_args['no-j2']:
            show_error(None, 'j2-off')
            return sanic.response.text('Jinja2 is turned off, I can\'t serve Jinja2 files', status=500)

        if run_args['no-php']:
            show_error(None, 'php-off')
            return sanic.response.text('PHP is turned off, I can\'t serve PHP files', status=500)

        myargs = request.args
        for k, value in myargs.items():
            myargs[k] = value[0]
        template = jinja2.Template(text)
        res = template.render(myargs)
        with open(f'{path.split(".")[-3]}.php', 'w') as file:
            file.write(res)
        res = compile_php(f'{path.split(".")[-3]}.php', debug=debug)
        os.remove(f'{path.split(".")[-3]}.php')
        if run_args['auto-refresh']:
            res = res.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        return sanic.response.html(res)

    elif run_args['index'].endswith('.php'):
        if run_args['no-php']:
            show_error(None, 'php-off')
            return sanic.response.text('PHP is turned off, I can\'t serve PHP files', status=500)

        res = compile_php(path, debug=debug)
        if run_args['auto-refresh']:
            res = res.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        return sanic.response.html(res)

    elif run_args['index'].endswith('.html') or run_args['index'].endswith('htm'):
        if run_args['auto-refresh']:
            text = text.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        return sanic.response.html(text)

    elif run_args['index'].endswith('.jinja2') or run_args['index'].endswith('.j2'):
        if run_args['no-j2']:
            show_error(None, 'j2-off')
            return sanic.response.text('Jinja2 is turned off, I can\'t serve Jinja2 files', status=500)

        myargs = request.args
        if run_args['auto-refresh']:
            text = text.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        template = jinja2.Template(text)
        return sanic.response.html(template.render(myargs))

    else:
        show_error(None, 'index-incorrect-format')
        return sanic.response.text('Expected index file to be .php, .j2 or .html', status=500)


@app.get('/assets/<path>')
async def assets(_, path: str):
    if path.endswith('.css'):
        loc_path = Path(f'assets/css/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/css')

    elif path.endswith('.js'):
        loc_path = Path(f'assets/js/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/javascript')

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
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/plain')


@app.route('/<path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
async def resource(request: Request, path: str):
    if 'AUTOREFRESH' in request.args and request.args['AUTOREFRESH'] == ['true']:
        debug = False
    else:
        debug = True

    try:
        text = Path(path).read_text('utf-8')
    except FileNotFoundError:
        show_error(None, '404')
        return sanic.response.text('404 Not Found', status=404)

    if path.endswith('.jinja2.php') or path.endswith('.j2.php'):
        if run_args['no-j2']:
            show_error(None, 'j2-off')
            return sanic.response.text('Jinja2 is turned off, I can\'t serve Jinja2 files', status=500)

        if run_args['no-php']:
            show_error(None, 'php-off')
            return sanic.response.text('PHP is turned off, I can\'t serve PHP files', status=500)

        myargs = request.args
        for k, value in myargs.items():
            myargs[k] = value[0]
        template = jinja2.Template(text)
        res = template.render(myargs)
        with open(f'{path.split(".")[-3]}.php', 'w') as file:
            file.write(res)
        res = compile_php(f'{path.split(".")[-3]}.php', debug=debug)
        if run_args['auto-refresh']:
            res = res.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        os.remove(f'{path.split(".")[-3]}.php')
        return sanic.response.html(res)

    elif path.endswith('.php'):
        if run_args['no-php']:
            show_error(None, 'php-off')
            return sanic.response.text('PHP is turned off, I can\'t serve PHP files', status=500)

        res = compile_php(path, debug=debug)
        if run_args['auto-refresh']:
            res = res.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        return sanic.response.html(res)

    elif path.endswith('.html') or path.endswith('htm'):
        if run_args['auto-refresh']:
            text = text.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        return sanic.response.html(text)

    elif path.endswith('.jinja2') or path.endswith('.j2'):
        if run_args['no-j2']:
            show_error(None, 'j2-off')
            return sanic.response.text('Jinja2 is turned off, I can\'t serve Jinja2 files', status=500)

        myargs = request.args
        for k, value in myargs.items():
            myargs[k] = ' '.join(value).strip()
        if run_args['auto-refresh']:
            text = text.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        template = jinja2.Template(text)
        return sanic.response.html(template.render(myargs))

    else:
        return sanic.response.text(text)


@app.exception(sanic.exceptions.NotFound)
async def not_found(_, __):
    show_error(None, '404')
    return sanic.response.text('404 Not Found', status=404)


# Any other exception
@app.exception(Exception)
async def server_error(_, exc: Exception):
    if exc.args[0] != 'PHP parsing error':
        show_error(None, '500')

    return sanic.response.text('500 Internal Server Error', status=500)


if __name__ == '__main__':
    c.print(f'[green bold]Server started![/green bold]\nAccess it on http://localhost:{run_args["port"]}\n')
    c.print('[white bold]Configuration[/white bold]')
    for key, value in run_args.items():
        c.print(f'  [bright_black italic]{key}[/bright_black italic]: {value}')

    c.print('\n[bright_black italic]Press Ctrl+C to stop the server[/bright_black italic]\n')
    app.run(host='localhost', port=run_args['port'], debug=False)
    c.print(f'[red bold]Server stopped![/red bold]')
