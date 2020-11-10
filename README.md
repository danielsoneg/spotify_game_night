# Spotify "Game Night" App
## TL;DR:
```
$ cp docker/template.env docker.prod.env && vim docker/prod.env
$ docker-compose --env-file docker/prod.env -f docker/docker-compose.yml --project-directory=. up
```

## What does it do?
This is a small app designed to keep a list of users in sync with a chosen spotify account. It was designed to allow a group of us to share a soundtrack for game nights.

### That seems like overkill.
Probably! I needed a project, and I wanted to play with Python's new asyncio library, and this seemed like more fun than trying to figure out which of the 900 other solutions actually worked.

## How do I use it?
First, a precaution: This was written in about 2 weeks for personal use. It has not been exhaustively tested, and there are probably a lot of rough edges. This should _not_ be considered a production-ready app, and you run it at your own risk.

### TL;DR:
`$ docker-compose --env-file docker/prod.env -f docker/docker-compose.yml --project-directory=. up`

### Config:
There's a docker compose file that will bring up the worker, server, and a Redis instance. You'll need to set up a Spotify developer account and create the Docker environment file - check `docker/template.env` for the syntax. Note that **EVERY LISTENER MUST HAVE SPOTIFY PREMIUM**. I didn't make the rules, I just stumbled into them during development.

### Components:
#### `serve.py`
The web server. Built using [Quart](https://gitlab.com/pgjones/quart), which is like Flask but with `async` in front of everything. Presents by default on port 5000.
#### `worker.py`
The sync worker. It's a single process Python service that uses asyncio extensively to juggle the spotify clients. Once set up, it runs a loop every two seconds which:
1. Checks that there is a main user
2. Checks what that main user is playing. If that's new, then:
3. Grabs all of the known listener tokens
4. Starts the new track on all of the listeners
5. Restarts the new track on the main user's account.

#### redis
I've used Redis a lot in the past and it's generally been stable, sane, and reliable. There's also provisions for just storing everything to the filesystem, which is how I started with this, but I recommend using redis, because it's already set up and ready to go. The redis instance does _not_ have auth or redundancy configured.

## I found a bug!
I don't doubt it! Submit a pull request and I'll be grateful!