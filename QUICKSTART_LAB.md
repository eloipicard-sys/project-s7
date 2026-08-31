# Running the application in the lab

Short guide for the closed-loop measurement session.
Everything runs in Docker on a machine connected to the laboratory network.

---

## 1. Get the code

```bash
git clone https://github.com/eloipicard-sys/project-s7.git
cd project-s7
```

If you already cloned it earlier, pull the latest version instead — the identification
now acts on the **heater PWM**, not on the flow setpoint:

```bash
git pull
```

## 2. Configure the PLC address

```bash
cp .env.example .env
```

The defaults should already be correct for the lab:

```
PLC_IP=192.168.1.10
PLC_RACK=0
PLC_SLOT=1
```

If the CPU has a different address, edit `.env` before starting.

## 3. Start

```bash
docker compose up -d --build
```

The first build takes a few minutes. Then check it is alive:

```bash
curl http://localhost:5000/health
```

Expected answer: `{"status":"ok"}`

## 4. Open the interface

| Page | URL | Use |
|---|---|---|
| **Cascade** | http://localhost:5000/cascade | **the one we need** — identification and control |
| Synoptic | http://localhost:5000/schema | live P&ID overview |
| Process tags | http://localhost:5000/process | all 21 tags, for debugging |
| Monitor | http://localhost:5000/ | trend chart and CSV export |

From another machine on the lab network, replace `localhost` with the IP of the machine
running Docker.

---

## Checking the connection

On the **Process** page, the badge at the top right shows the data source:

- `OPENPIPE` or `SNAP7` — connected to the PLC, real values
- `SIMULATION` — no PLC reachable, values are synthetic

If it shows `SIMULATION` while the PLC is on, check `PLC_IP` in `.env`, then restart:

```bash
docker compose down && docker compose up -d
```

---

## During the session

The three runs are described in the protocol I sent separately. In short, from the
**Cascade** page:

1. Confirm the controller is in **MANUAL** before anything else
2. Set the hot circuit flow to the operating point
3. Switch to **AUTO-INNER**, then apply the setpoint step
4. The chart records automatically; nothing else to do

At the end, export the log:

```
http://localhost:5000/api/export/csv
```

Or from the Monitor page, "Export CSV" button.

---

## Two things to check on the PLC side

- **The heater PWM tag.** The application writes to a tag provisionally named
  `HeaterLarge_PWM`. Could you confirm its real symbolic name and address in TIA Portal?
  If it differs, it needs to be changed in `app/openpipe_connector.py` and `app/main.py`.

- **DB1 must have Optimized block access disabled**, and now needs **36 bytes** from
  offset 28 (it was 28 bytes): the application writes the identified gains back to
  `DBD56` (krPI) and `DBD60` (TiPI).

---

## Useful commands

```bash
docker compose logs -f      # follow the logs
docker compose restart      # restart after editing .env
docker compose down         # stop everything
```

The `app/` directory is mounted into the container, so any Python change takes effect
without rebuilding.
