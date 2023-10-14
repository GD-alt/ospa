import logging
import os
import subprocess
from pathlib import Path
import zipfile
import time
import datetime
from traceback import format_exc as fe
from textwrap import indent
from argparse import ArgumentParser

parse_error_snippet = """<!DOCTYPE html>
<head>
<meta charset="utf-8">
<title>Reverse String</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<html>
<body>

<p><b>Oops! PHP parsing error, sweetie!</b></p>

</body>
</html>"""

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
    subprocess.run(["py", "-m", "pip", "install", "rich"])
    from rich.console import Console

    c = Console()
    c.print('[green]rich installed![/green]\n')

from rich.live import Live

try:
    import sanic

    import sanic.response
    from sanic.request import Request
    import sanic.exceptions
    from sanic import Sanic
except ModuleNotFoundError:
    c.print('[grey italic]sanic not found, attempting to install…[/grey italic]')
    subprocess.run(["py", "-m", "pip", "install", "sanic"])
    c.print('[green]sanic installed![/green]\n')
    import sanic

    import sanic.response
    from sanic.request import Request
    import sanic.exceptions
    from sanic import Sanic

try:
    import yaml
except ModuleNotFoundError:
    c.print('[grey italic]yaml not found, attempting to install…[/grey italic]')
    subprocess.run(["py", "-m", "pip", "install", "pyyaml"])
    import yaml

    c.print('[green]yaml installed![/green]\n')

available_args = {
    'port': (('-p', '--port'), 'Port to run server on'),
    'php-path': (('-pp', '--php-path'), 'Path to PHP CGI executable'),
    'config-path': (('-c', '--config-path'), 'Path to config file'),
    'index': (('-i', '--index'), 'Path to index file'),
    'log-requests': (('-l', '--log'), 'If requests should be logged'),
    'auto-refresh': (('-r', '--refresh'), 'If auto-refresh should be enabled'),
    'no-php': (('-np', '--no-php'), 'Disable PHP support'),
    'no-j2': (('-nj', '--no-j2'), 'Disable Jinja2 support'),
    'no-assets-serve': (('-na', '--no-assets'), 'Disable assets serving (assets will be served from '
                                                      'the main folder)'),
    'serve-dir': (('-sd', '--serve-dir'), 'Directory to serve files from'),
}

parser = ArgumentParser(description='OpenServer Portable Alternative')
default_values = {
    'port': 12521,
    'php-path': 'php/php-cgi.exe',
    'config-path': 'config.yaml',
    'index': 'index.php',
    'log-requests': False,
    'auto-refresh': False,
    'no-php': False,
    'no-j2': False,
    'no-assets-serve': False,
    'serve-dir': '.'
}

for key, value in available_args.items():
    if isinstance(value[1], bool):
        parser.add_argument(*value[0], action='store_true', default=None, help=value[1])
    else:
        parser.add_argument(*value[0], default=None, type=type(default_values[key]),
                            help=value[1])


def get_cli_args(cli_parser):
    crun_args = vars(cli_parser.parse_args())
    for k, val in available_args.items():
        crun_args[k] = crun_args[val[0][1].strip('-').replace('-', '_')]

    crun_args = {k: val for k, val in crun_args.items() if k in available_args}

    if not crun_args['config-path']:
        crun_args['config-path'] = 'config.yaml'

    if not Path(crun_args['config-path']).exists():
        c.print(f'[yellow]Config file not found on {crun_args["config-path"] or default_values["config-path"]}'
                f', creating…[/yellow]')

        sanit = {k: v for k, v in default_values.items() if k != 'config-path'}

        Path(crun_args['config-path']).write_text(yaml.dump(sanit))

        c.print(f'[green]Config file created![/green]\n')

    else:
        run_args_live = yaml.load(Path(crun_args['config-path']).read_text('utf-8'), Loader=yaml.FullLoader)
        for k, val in crun_args.items():
            if val is None:
                crun_args[k] = run_args_live.get(k, default_values[k])

    return crun_args


run_args = get_cli_args(parser)

if not run_args['no-j2']:
    try:
        import jinja2
    except ModuleNotFoundError:
        c.print('[grey italic]jinja2 not found, attempting to install…[/grey italic]')
        subprocess.run(["py", "-m", "pip", "install", "jinja2"])
        import jinja2

        c.print('[green]jinja2 installed![/green]\n')


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
        c.print(f'  [indian_red bold]PHP compiled with unknown encoding![/indian_red bold]')
    elif spec == 'non-utf-8-encoding':
        c.print(f'  [indian_red bold]PHP compiled with non-UTF-8 encoding![/indian_red bold]\n'
                f'    It usually happens when PHP messes up with bytes — using cp1251, but check your code,'
                f'this is not intended to happen in the most cases.')
    elif spec == 'php-off':
        c.print(f'  [dark_orange bold]Alert:[/dark_orange bold] PHP is turned off, I can\'t serve PHP files')
    elif spec == 'j2-off':
        c.print(f'  [dark_orange bold]Alert:[/dark_orange bold] Jinja2 is turned off, I can\'t serve Jinja2 files')
    elif spec == 'no-assets-serve':
        c.print(f'  [dark_orange bold]Alert:[/dark_orange bold] Assets serving is turned off, I can\'t serve assets')
    else:
        c.print(f'  [yellow bold]Warning:[/yellow bold] unknown error: {spec}')


def compile_php(filename: str, params: dict = None, debug: bool = False) -> str:
    """
    Compiles PHP data to HTML data
    :param filename: PHP data
    :param params: Request params
    :param debug: Debug mode
    :return: HTML data
    """
    if params is None:
        params = {}

    filepath = Path(prepath) / filename

    if not filepath.exists():
        raise FileNotFoundError(f'File {filename} not found')

    if not filename.endswith('.php'):
        raise ValueError(f'File {filename} is not a PHP file')

    cmd = [php_path, filepath.as_posix(), '--no-header']
    for param, vals in params.items():
        if len(vals) == 1:
            cmd.append(f'{param}={vals[0]}')
            continue

        for val in vals:
            cmd.append(f'{param}[]={val}')

    res_bytes = subprocess.run(cmd, capture_output=True).stdout

    try:
        res = res_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            res = res_bytes.decode('cp1251')
            if debug:
                show_error(None, 'non-utf-8-encoding')
        except UnicodeDecodeError:
            if debug:
                show_error(None, 'encoding?')
                raise Exception('PHP compiled with unknown encoding!')
            else:
                return parse_error_snippet

    if res.startswith('\nParse error') and debug:
        show_error(res.removeprefix('\nParse error: '), 'php')
        raise Exception('PHP parsing error')

    i = res.find('<!DOCTYPE html>')
    return res[i:]


php_path = run_args['php-path']

if not Path(php_path).exists() and not run_args['no-php']:
    if not (c.input(f'[yellow]PHP not found on {run_args["php-path"]}\nAttempt an installation?[/yellow] '
                    f'(Y/N) ').lower() in ('y', 'yes')):
        c.print('[red]PHP not found, exiting…[/red]')
        exit(1)
    else:
        try:
            import requests
        except ModuleNotFoundError:
            c.print('[grey italic]requests not found, attempting to install…[/grey italic]')
            subprocess.run(["py", "-m", "pip", "install", "requests"])
            import requests

            c.print('[green]requests installed![/green]\n')

        php_path = Path(php_path)
        php_path.parent.mkdir(exist_ok=True)

        r = requests.get('https://windows.php.net/downloads/releases/php-8.2.11-nts-Win32-vs16-x64.zip',
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

prepath = run_args['serve-dir']


@app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
async def index(request: Request):
    if 'AUTOREFRESH' in request.args and request.args['AUTOREFRESH'] == ['true']:
        debug = False
    else:
        debug = True

    path = run_args['index']

    try:
        text = (Path(prepath) / path).read_text('utf-8')
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
        for k, val in myargs.items():
            myargs[k] = val[0]
        template = jinja2.Template(text)
        res = template.render(myargs)
        with open(f'{path.split(".")[-3]}.php', 'w') as file:
            file.write(res)
        res = compile_php(f'{path.split(".")[-3]}.php', request.args, debug=debug)
        os.remove(f'{path.split(".")[-3]}.php')
        if run_args['auto-refresh']:
            res = res.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        return sanic.response.html(res)

    elif run_args['index'].endswith('.php'):
        if run_args['no-php']:
            show_error(None, 'php-off')
            return sanic.response.text('PHP is turned off, I can\'t serve PHP files', status=500)

        res = compile_php(path, request.args, debug=debug)
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


@app.get('/assets/<path:path>')
async def assets(_, path: str):
    if run_args['no-assets-serve']:
        show_error(None, 'no-assets-serve')
        await resource(_, path)

    if path == 'refresh.js':
        return sanic.response.text(inject_js, content_type='text/javascript')

    elif path.endswith('.css'):
        loc_path = Path(prepath, f'assets/css/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/css')

    elif path.endswith('.js'):
        loc_path = Path(prepath, f'assets/js/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/javascript')

    elif path.split('.')[-1] in ('png', 'jpg', 'jpeg', 'gif', 'ico'):
        loc_path = Path(prepath, f'assets/img/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return await sanic.response.file(loc_path)

    elif path.split('.')[-1] in ('ttf', 'woff', 'woff2'):
        loc_path = Path(prepath, f'assets/fonts/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return await sanic.response.file(loc_path)

    else:
        loc_path = Path(prepath, f'assets/{path}')
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/plain')


@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
async def resource(request: Request, path: str):
    if 'AUTOREFRESH' in request.args and request.args['AUTOREFRESH'] == ['true']:
        debug = False
    else:
        debug = True

    pars = {k: ' '.join(val) for k, val in request.args.items() if k != 'AUTOREFRESH'}

    try:
        text = (Path(prepath) / path).read_text('utf-8')
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
        for k, val in myargs.items():
            myargs[k] = val[0]
        template = jinja2.Template(text)
        res = template.render(myargs)
        with open(f'{path.split(".")[-3]}.php', 'w') as file:
            file.write(res)
        res = compile_php(f'{path.split(".")[-3]}.php', pars, debug=debug)
        if run_args['auto-refresh']:
            res = res.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        os.remove(f'{path.split(".")[-3]}.php')
        return sanic.response.html(res)

    elif path.endswith('.php'):
        if run_args['no-php']:
            show_error(None, 'php-off')
            return sanic.response.text('PHP is turned off, I can\'t serve PHP files', status=500)

        res = compile_php(path, pars, debug=debug)
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
        for k, val in myargs.items():
            myargs[k] = ' '.join(val).strip()
        if run_args['auto-refresh']:
            text = text.replace('</body>', '    <script src="assets/refresh.js"></script></body>')
        template = jinja2.Template(text)
        return sanic.response.html(template.render(myargs))

    elif path == 'refresh.js' and run_args['no-assets-serve']:
        return sanic.response.text(inject_js, content_type='text/javascript')

    elif path.endswith('.css') and run_args['no-assets-serve']:
        loc_path = Path(path)
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/css')

    elif path.endswith('.js') and run_args['no-assets-serve']:
        loc_path = Path(path)
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/javascript')

    elif path.split('.')[-1] in ('png', 'jpg', 'jpeg', 'gif', 'ico') and run_args['no-assets-serve']:
        loc_path = Path(path)
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return await sanic.response.file(loc_path)

    elif path.split('.')[-1] in ('ttf', 'woff', 'woff2') and run_args['no-assets-serve']:
        loc_path = Path(path)
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return await sanic.response.file(loc_path)

    else:
        loc_path = Path(path)
        if not loc_path.exists():
            show_error(None, 'no-resource')
            return sanic.response.text('404 Not Found', status=404)
        return sanic.response.text(loc_path.read_text('utf-8'), content_type='text/plain')


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
    run_args = get_cli_args(parser)
    c.print(f'[green bold]Server started![/green bold]\nAccess it on http://localhost:{run_args["port"]}\n')
    c.print('[white bold]Configuration[/white bold]')
    for key, value in run_args.items():
        c.print(f'  [bright_black italic]{key}[/bright_black italic]: {value}')

    c.print('\n[bright_black italic]Press Ctrl+C to stop the server[/bright_black italic]\n')
    app.run(host='localhost', port=run_args['port'], debug=False)
    c.print(f'[red bold]Server stopped![/red bold]')
