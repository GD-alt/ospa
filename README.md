# ospa
### OpenServer Portable Alternative

**DISCLAIMER:** I'm not porting this for Linux, because OSP is a piece of shit nobody needs, and even more so for Windows only.
**DISCLAIMER 2:** Yep, it's truly shitty code, don't shitcode-blame me.

## Introduction
In general terms, OSPA is a small script with Sanic under the hood to serve HTML/PHP pages in the folder where the script is running. Jinja2 is also supported — save files with `jinja2` and `j2` extensions, the required parameters are passed in the query string. I have no fucking clue why you might want to do this, but you can combine Jinja2 with PHP by saving files with the extension `jinja2.php` or `j2.php`. All scripts, images, fonts and styles should be saved in the `assets` folder in the `js`, `img`, `fonts` and `css` subfolders respectively. Script is used via CLI ind installs all requirements, including PHP itself, automatically (if the path to it is not specified).

## Configuration
OSPA has a configuration file stored in the folder where the script resides. It is saved in YAML format — if you are not satisfied with it, you can go fuck yourself. If there's no config file present, the script will create it by itself for you, you miserable piece of shit. At this moment, there's such options:

|  **Option**  |                                                            **Description**                                                           | **Default value** | **Data type** |
|:------------:|:------------------------------------------------------------------------------------------------------------------------------------:|:-----------------:|:-------------:|
| config-path  | Path to the config file.                                                                                                             | config.yaml       | str           |
| index        | Index page.                                                                                                                          | index.html        | str           |
| php-path     | Path to the **PHP executable**. If not present, will be created.                                                                    | php/php.exe       | str           |
| port         | Port on which to run a server.                                                                                                       | 12521             | int           |
| log-requests | If OSPA should log time, method and path of incoming requests in fucking awesome, truly beautiful, incomprehensibly good formatting. | false             | bool          |

## Usage
Use `python ospa.py`. CLI also provides the same set of options.

|  **Option**  | **CLI alt (short)** | **CLI alt (long)** |
|:------------:|:-------------------:|:------------------:|
| config-path  | -c                  | --config-path      |
| index        | -i                  | --index            |
| php-path     | -pp                 | --php-path         |
| port         | -p                  | --port             |
| log-requests | -l                  | --log              |

