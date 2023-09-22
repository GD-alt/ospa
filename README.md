# ospa
### OpenServer Portable Alternative

**DISCLAIMER: ospa is *not for production* use.** By default, it uses php-cgi.exe, which has possible vulnerabilities. Please read [CGI security section](https://www.php.net/manual/en/security.cgi-bin.php) on official PHP site. 

**DISCLAIMER:** I'm not porting this for Linux, because OSP is a piece of shit nobody needs, and even more so for Windows only. 

**DISCLAIMER 2:** Yep, it's truly shitty code, don't shitcode-blame me.

**DISCLAIMER 3:** Yeah, I know if you transliterate `ospa` to Russian, you'll get `оспа` and it means `pox` lol

## Introduction
In general terms, OSPA is a small script with Sanic under the hood to serve HTML/PHP pages in the folder where the script is running. Jinja2 is also supported — save files with `jinja2` and `j2` extensions, the required parameters are passed in the query string. I have no fucking clue why you might want to do this, but you can combine Jinja2 with PHP by saving files with the extension `jinja2.php` or `j2.php`. All scripts, images, fonts and styles should be saved in the `assets` folder in the `js`, `img`, `fonts` and `css` subfolders respectively. Script is used via CLI ind installs all requirements, including PHP itself, automatically (if the path to it is not specified).

## Configuration
OSPA has a configuration file stored in the folder where the script resides. It is saved in YAML format — if you are not satisfied with it, you can go fuck yourself. If there's no config file present, the script will create it by itself for you, you miserable piece of shit. At this moment, there's such options:

|   **Option**    |                                                                                            **Description**                                                                                             | **Default value** | **Data type** |
|:---------------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|:-----------------:|:-------------:|
|   config-path   |                                                                                        Path to the config file.                                                                                        |    config.yaml    |      str      |
|      index      |                                                                                              Index page.                                                                                               |    index.html     |      str      |
|    php-path     |                                                                    Path to the **PHP executable**. If not present, will be created.                                                                    |  php/php-cgi.exe  |      str      |
|      port       |                                                                                     Port on which to run a server.                                                                                     |       12521       |      int      |
|  log-requests   |                                  If OSPA should log time, method and path of incoming requests in fucking awesome, truly beautiful, incomprehensibly good formatting.                                  |       false       |     bool      |
|  auto-refresh   |                                            If OSPA should automatically update the page contents as HTML/PHP/Jinja2/CSS/JS contents update (*hot reload*).                                             |       false       |     bool      |
|     no-php      |                                                                   If you are going to ruin all the fun and run OSPA in no-PHP mode.                                                                    |       false       |     bool      |
|      no-j2      |                                                                If you are going to ruin part of the fun and run OSPA in no-Jinja2 mode.                                                                |       false       |     bool      |
| no-assets-serve |                                                         If OSPA should serve static assets (like styles and scripts) from the main directory.                                                          |       false       |     bool      |
|    serve-dir    | If you don't need to serve contents of the folder, where script is located, you can specify another path (autorefresh script will be still on the same path, because it's not a really existing file). |         .         |    string     |


## Usage
Use `python ospa.py`. CLI also provides the same set of options.

|   **Option**    | **CLI alt (short)** | **CLI alt (long)** |
|:---------------:|:-------------------:|:------------------:|
|   config-path   |         -c          |   --config-path    |
|      index      |         -i          |      --index       |
|    php-path     |         -pp         |     --php-path     |
|      port       |         -p          |       --port       |
|  log-requests   |         -l          |       --log        |
|  auto-refresh   |         -r          |     --refresh      |
|     no-php      |         -np         |      --no-php      |
|      no-j2      |         -nj         |      --no-j2       |
| no-assets-serve |         -na         |    --no-assets     |
|    serve-dir    |         -sd         |    --serve-dir     |

