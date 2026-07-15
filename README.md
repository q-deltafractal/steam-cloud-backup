# steam-cloud-backup

micro-script for downloading all save files from [steam cloud](https://store.steampowered.com/account/remotestorage)

<br>

## installation

from [PyPI](https://pypi.org/project/steam-cloud-backup/):

```bash
# with uv
uv tool install steam-cloud-backup
```

```bash
# or pipx
pipx install steam-cloud-backup
```

```bash
# or with pip
pip install steam-cloud-backup
```

from source:

```bash
# clone source
git clone https://github.com/q-deltafractal/steam-cloud-backup.git
cd steam-cloud-backup
# run script
uv run steamcb/cli.py
```

<br>

## usage

```console
$ steam-cloud-backup out/
steamLoginSecure: <input>
INFO:__main__:iter game: Steam Client; files count: 2
...
INFO:__main__:backup success
```

<br>

To identify login to your account, steam uses `steamLoginSecure` cookie, therefore the script requires it to work.  
Method of obtaining this cookie:

- [ ] log in to https://store.steampowered.com/login/
- [ ] open Dev Tools via `ctrl + shift + i`
- [ ] go to the application _(or storage)_ tab
- [ ] in the cookies section, select `https://store.steampowered.com`
- [ ] copy the entire contents of the `steamLoginSecure` row

<br>

```console block=api

usage: steamcb [-h] [-i SESSIONID] [-l STEAMLOGINSECURE]
               [-j MAX_CONCURRENT_CONNECTIONS]
               [--connect-timeout CONNECT_TIMEOUT] [--useragent USERAGENT]
               [-v (0, 1, 2)]
               folder

micro-script for downloading all save files from steam cloud

options:
  -h, --help            show this help message and exit

session:
  -i, --sessionId SESSIONID
  -l, --steamLoginSecure STEAMLOGINSECURE

connection:
  -j, --max-concurrent-connections MAX_CONCURRENT_CONNECTIONS
                        default: 16
  --connect-timeout CONNECT_TIMEOUT
                        default: 60 (s)
  --useragent USERAGENT

out:
  folder
  -v, --verbose (0, 1, 2)
                        logging type: 0 - off; 1 (default) - info; 2 - debug
```

<br>

## license

project is licensed under:

<table>
  <tr>
    <td>
      MIT
    </td>
    <td>
      <a href="LICENSE">LICENSE</a>
    </td>
    <td>
      https://mit-license.org/
    </td>
  </tr>
</table>
