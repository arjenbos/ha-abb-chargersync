# Local testing with Docker Compose

The repository includes an isolated Home Assistant Container setup for testing the ChargerSync integration. It uses the version exercised by the Python tests, 2026.10.3, by default. No image build or local Python environment is needed to run Home Assistant.

## Start

Start your Docker-compatible Linux container runtime, then run these commands from the repository root:

```sh
docker compose config --quiet
docker compose up -d
docker compose logs -f homeassistant
```

Open [http://localhost:8123](http://localhost:8123) and complete Home Assistant onboarding. Create a local Home Assistant user; this is separate from your ChargerSync account.

Then open **Settings → Devices & services → Add integration → ABB ChargerSync** and sign in with your ChargerSync account. Link the charger in the official app first. Tokens and local accounts are stored only in the ignored development data directory.

This setup calls the real ChargerSync cloud when you add the integration. It is not the test suite's simulated server. Charging buttons and other controls operate the linked charger when its connection succeeds.

## Files and mounts

| Repository path | Container path | Purpose |
|---|---|---|
| `.local/homeassistant/` | `/config` | Persistent local accounts, tokens, logs, database, and dashboard storage; ignored by Git |
| `development/configuration.yaml` | `/config/configuration.yaml` | Read-only, version-controlled Home Assistant configuration |
| `custom_components/abb_chargersync/` | `/config/custom_components/abb_chargersync` | Read-only mount of the integration under development |
| `custom_components/abb_chargersync/brand/` | `/config/www/abb_chargersync` | Read-only dashboard logo and icon assets |

Docker creates `.local/homeassistant/` on first startup. The configuration file is mounted over that directory, so edit `development/configuration.yaml` in the repository when changing configuration. Do not put credentials in that file.

The HTTP port is bound to the local host only. This cloud-development setup uses normal bridge networking and does not require privileged mode, host networking, USB access, or D-Bus. Host discovery and Bluetooth/hardware testing are outside its scope. It is not a production Home Assistant deployment.

## Change code and reload

Source files are mounted directly, so rebuilding an image is unnecessary. Restart Home Assistant after Python changes:

```sh
docker compose restart homeassistant
```

Watch integration logs:

```sh
docker compose logs -f homeassistant
```

For more detailed integration logs, change its level from `info` to `debug` in `development/configuration.yaml` and restart. Avoid enabling verbose logs for unrelated HTTP libraries when handling account tokens.

## Check Home Assistant configuration

With the container running:

```sh
docker compose exec homeassistant python -m homeassistant --script check_config --config /config
```

This validates Home Assistant configuration. It does not verify the vendor cloud protocol or the correctness of charger commands.

## Try the Lovelace dashboard

Follow the [dashboard setup guide](dashboard.md) and import the generated YAML into a new dashboard using its Raw configuration editor. The Compose setup already serves the header icon at `/local/abb_chargersync/icon.png`; no extra icon-copy step is needed.

Match entity IDs to the device names created by this local instance. The Python dashboard generator is optional; you can also edit the entity IDs in the template manually.

## Override version, port, or timezone

Defaults work without an environment file. To customize them:

```sh
cp .env.example .env
```

Edit `.env`, for example:

```dotenv
HA_VERSION=2026.10.3
HA_PORT=8124
TZ=Europe/Amsterdam
```

Then apply the changes:

```sh
docker compose up -d
```

Open `http://localhost:8124` when using the example port override. The container still listens on 8123, and the health check uses that internal port. Use Home Assistant 2026.10.0 or later; a different image version has not necessarily been tested with this integration.

To fetch a newly selected image explicitly:

```sh
docker compose pull
docker compose up -d
```

## Stop and preserve data

```sh
docker compose down
```

This removes the development container and network while preserving `.local/homeassistant/`. Starting again reuses the same Home Assistant instance. `docker compose down --volumes` also leaves this bind-mounted directory intact.

For a clean onboarding run, stop Compose, rename `.local/homeassistant/` to a backup directory within `.local/`, then start Compose again. Keep the backup private: it contains account tokens and local credentials.

## Troubleshooting

- **Cannot connect to the Docker daemon:** start the container runtime, then retry `docker compose up -d`.
- **Port already in use:** choose a different `HA_PORT` in `.env`.
- **Integration not listed:** wait for startup to finish, refresh the browser, and check `docker compose logs homeassistant` for import errors.
- **Code changes not taking effect:** restart the service. A bind mount updates files but does not reload imported Python modules automatically.
- **Read-only configuration file:** edit `development/configuration.yaml` on the host, not the overlaid file inside `/config`.
- **Container healthy but charger unavailable:** the health check only confirms that the local HTTP interface responds. Cloud authentication and charger connectivity are separate.

## References

- [Home Assistant Container setup](https://www.home-assistant.io/installation/linux/)
- [Docker Compose lifecycle commands](https://docs.docker.com/compose/support-and-feedback/faq/)
