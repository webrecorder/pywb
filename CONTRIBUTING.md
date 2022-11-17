# pywb contributing guide

Thank you for your interest in contributing to pywb and open source web archiving tools!

If you have a question not covered below or are interesting in collaborating, please feel free to reach out via any of our [contact points](https://webrecorder.net/contact).

## How to contribute to pywb

### I found a bug

Please take a look at the [open issues](https://github.com/webrecorder/pywb/issues) to see if someone else has already described the same issue and if so, leave any comments or suggestions there.

If no such issue already exists, feel free to [open a new issue](https://github.com/webrecorder/pywb/issues/new/choose) using the Bug Report template. If the bug is specifically related to replay of a particular site, instead use the Replay Issue template.

When opening an issue or commenting on an open issue, please describe the problem you are having, any steps required to reproduce the bug (including the pywb version affected), and include any contextual information or screenshots that may be helpful.

### I wrote a patch to fix a bug

Please open a new pull request with a description of the changes and a link to the related issue (if no issue yet exists, please create one first).

Create a new branch with a short descriptive name including the issue number, based on the latest `main` branch.

All changes should be submitted with test coverage for the change as well as updates to the project documentation if appropriate.

Avoid making unnecessary changes such as reformatting code or otherwise touching parts of the codebase that are not directly relevant to the issue at hand.

We do our best to review pull requests in a timely manner but as we are a small team with many projects we cannot guarantee a response or merging timeline. Webrecorder reserves the right to reject pull requests that do not fit the direction of the project or ethics of the Webrecorder project.

The Development section below has information on how to get started with working on pywb in a local development environment.

### I want to propose a new feature

Please take a look at the [open issues](https://github.com/webrecorder/pywb/issues) to see if someone else has already proposed a similar feature and if so, leave any comments or suggestions there.

If no such issue already exists, feel free to [open a new issue](https://github.com/webrecorder/pywb/issues/new/choose) using the Feature Request template.

## Development

The [pywb documentation](https://pywb.readthedocs.io/en/latest/) contains information on pywb's architecture, configuration file, and how to get started with the software locally or in a Docker container.

The project root directory contains a basic [Docker Compose](https://docs.docker.com/compose/) configuration file, which can be used to easily start a development environment. After installing Docker Desktop and Docker Compose (if not installed with Desktop), to run pywb in detached mode on `localhost:8080`, run:

```bash
docker compose up -d
```

(Note: this example assumes a newer version of Docker Desktop. For older versions that did not bundle Compose, you may need to replace `docker compose` with `docker-compose`)

The first time you run this command, it make take some time to build.

Changes to the [Vue](https://vuejs.org/) frontend components require rebuilding the Vue bundle (`pywb/static/vue/vueui.js`) to take effect. After making changes to one or more Vue components, you can rebuild the static bundle and view the changes in your development environment like so:

```bash
cd pywb/vueui
yarn run build
cd ../..
docker compose up -d --force-recreate
```

Changes that modify pywb's Python dependencies or the operating system may require rebuilding the container:

```bash
docker compose up -d --build --force-recreate
```

To stop the container:

```bash
docker compose down
```
