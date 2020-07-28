# Spotify "Game Night" App
## TL;DR:
```
$ pip install -r requirements.txt
$ cp config.template.ini config.ini && vim config.ini
$ ln -s $your_webroot/static ./static
$ python serve.py &
$ python worker.py
```

## What does it do?
This is a small app designed to keep a list of users in sync with a chosen spotify account. It was designed to allow a group of us to share a soundtrack for game nights.

### That seems like overkill.
Probably! I needed a project, and I wanted to play with Python's new asyncio library, and this seemed like more fun than trying to figure out which of the 900 other solutions actually worked.

## How do I use it?
If you've any sense, don't. If you do, you do so at your own risk.

This was written in about 5 days for personal use. There is **Absolutely Nothing** about this app that should be considered production ready. Chief among its flaws is that the data store is the file system, so both the server and the worker need to be able to read the same path in the filesystem. This was a design decision arrived at after carefully considering that I didn't care and didn't want to set up redis or something for a stupid weekend project with four users. 

### But for real?
Requirements are listed in `requirements.txt`, as is the way of our people.

You'll need to set up a Spotify developer account and create the config.ini file - it's pretty simple, there's a template. Note that **EVERY LISTENER MUST HAVE SPOTIFY PREMIUM**. I didn't make the rules, I just stumbled into them during development.

I didn't spend any time on the run model - I'm just spinning up the server and worker in tmux sessions for game nights. 

The API server is a [Quart](https://gitlab.com/pgjones/quart) app, which is like Flask but with `async` in front of everything. Spin it up however you like to spin those sort of things up.

The worker is a single process Python service that uses asyncio extensively as well. The expected load is in the ~tens of users, and it is built accordingly. There is no affordance made for having multiple workers running.

As mentioned, the data store is files written to disk. Both the API server and the worker need read and write access to the store path. The store path can be configured in `config.ini`, although I didn't extensively guard against stupidity, so be careful where you point it.

## I found a bug!
I don't doubt it! Submit a pull request and I'll be grateful!

## You don't sound very helpful.
Normally I'm a pretty nice guy. This was a fun hack, not a product. I've put it up here primarily as a backup for myself and made it public on the off chance it's helpful to someone who sees it.

Also, I mean, there's comments and docstrings everywhere, and I wrote this. Really, who does that for a weekend project?