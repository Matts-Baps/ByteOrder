# ByteOrder

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

A self-serve kiosk ordering system for pop-up kitchens, garden kitchens, and small food venues. Customers scan a QR code on their phone, build their order, and track it in real time. The kitchen sees a live order queue and can print tickets to a Bluetooth receipt printer.

---

## How it works

1. You display a QR code (shown on the kiosk screen at `/`) that links customers to `/order`
2. Customers enter their name, pick items, customise toppings, and place the order
3. The kitchen admin panel shows a live queue — advance orders through **Pending → In Progress → Ready → Completed**
4. When an order is placed the print service fires a ticket to your Bluetooth printer
5. Customers can track their order status in real time on their phone

---

## Architecture

| Service | Stack | Purpose |
|---------|-------|---------|
| `frontend` | React + Vite + Tailwind | Mobile-first customer ordering UI, QR code home page |
| `admin` | React + Vite + Tailwind + Express | Menu management, order queue, settings, auth |
| `menu-service` | Python / FastAPI | CRUD for categories, items, ingredients, option groups, settings |
| `order-service` | Python / FastAPI + SSE | Order lifecycle, queue position, real-time status streaming |
| `print-service` | Python worker | Subscribes to Redis, POSTs formatted tickets to ble-printer-server |
| `postgres` | PostgreSQL 16 | Persistent store |
| `redis` | Redis 7 | Pub/sub for real-time SSE updates |

---

## Quick start — Docker Compose

### Prerequisites

- Docker with Compose v2
- A `.env` file in `deploy/` (see below)

### 1. Create `deploy/.env`

```env
POSTGRES_PASSWORD=changeme
JWT_SECRET=a-long-random-string-at-least-32-chars
ADMIN_DEFAULT_PASSWORD=changeme
```

> **JWT_SECRET** must be a strong random string. Generate one with:
> ```bash
> openssl rand -base64 32
> ```

### 2. Start the stack

```bash
cd deploy
docker compose up -d
```

### 3. Access the apps

| URL | What |
|-----|------|
| `http://localhost:3000` | Customer ordering frontend |
| `http://localhost:3001` | Kitchen admin panel |

### 4. First login

Default credentials: **admin / byteorder** (or whatever you set in `ADMIN_DEFAULT_PASSWORD`).

**Change the password immediately** — Admin → top-right menu → Change Password.

---

## Kubernetes / Helm deployment

### Prerequisites

- A running Kubernetes cluster
- Helm 3
- An existing PostgreSQL database and a Secret containing the DSN
- (Optional) [Dash0 operator](https://github.com/dash0hq/dash0-operator) for observability

### Install

```bash
helm install byteorder deploy/helm/byteorder \
  -n byteorder --create-namespace \
  -f your-values.yaml
```

### Key values

```yaml
# deploy/helm/byteorder/values.yaml (defaults shown)

imageTag: latest            # pin to a SHA for production

jwtSecret: ""               # REQUIRED — strong random secret, see above
adminDefaultPassword: ""    # initial admin password (change after first login)

postgres:
  enabled: true             # set false to use an external PostgreSQL cluster
  password: changeme
  storageSize: 2Gi
  # When enabled: false, provide a Secret with the full DSN:
  existingSecret: ""
  existingSecretKey: uri

ingress:
  enabled: true
  frontendHost: order.example.com
  adminHost: admin.example.com
  tls:
    enabled: true
    clusterIssuer: letsencrypt-prod

dash0:
  enabled: false            # set true if the Dash0 operator is installed
```

### Upgrade

```bash
helm upgrade byteorder deploy/helm/byteorder \
  -n byteorder --reuse-values
```

---

## Admin panel

### Menu setup

1. **Admin → Menu Management**
2. Create **Categories** (e.g. Burgers, Pizzas, Hot Dogs)
3. Add **Items** within each category (e.g. Normal Burger, Single Smash, Margherita)
4. **Admin → Ingredients** — create all your toppings (Cheese, Lettuce, Bacon, Jalapeños, etc.)
5. Back in **Menu Management**, attach ingredients to each item:
   - **First click** — outlined chip: ingredient is available as an **optional topping** (starts unselected for customers)
   - **Second click** — filled chip: ingredient is **pre-selected** by default
   - **Third click** — removes the ingredient from the item

   For a "plain by default" item (the recommended approach), use the first click only. Customers will see all toppings as unselected and tap to add what they want.

6. Use **Option Groups** (▼ button on each item) for mutually exclusive choices like "Size" (Small / Medium / Large)

### Branding

**Admin → Settings** lets you customise:
- Kitchen name (shown in the customer app and browser tab)
- Brand colours (primary, background, surface, text)
- Logo (uploaded as base64)

---

## Printer setup

ByteOrder prints via [ble-printer-server](https://github.com/proffalken/ble-printer-server) — a small HTTP server that drives a Bluetooth receipt printer.

### 1. Run ble-printer-server

On a Raspberry Pi (or any machine next to the printer):

```bash
docker run -d --privileged --net=host \
  ghcr.io/proffalken/ble-printer-server:latest
```

Note the machine's local IP address (e.g. `192.168.1.100`). The server listens on port `8080` by default.

### 2. Configure the printer URL in ByteOrder

**Admin → Settings → Printer URL**

Enter the full URL, e.g.:

```text
http://192.168.1.100:8080
```

The URL must:
- Use `http://` or `https://`
- Point to a reachable host on your network

LAN IP addresses (192.168.x.x, 10.x.x.x, 172.16–31.x.x) are explicitly allowed. `localhost` and Docker-internal service names are blocked as a security measure.

### 3. Test

Place a test order and mark it as **In Progress** — a ticket should print within a few seconds.

---

## QR code

The customer frontend (`/`) displays a QR code that links to `/order`. To use it:

1. Open `http://<your-host>:3000` on a screen customers can see (a tablet, a monitor at the counter, etc.)
2. Customers scan the QR code with their phone

The QR code URL is set via **Admin → Settings → Frontend URL**. Set this to the public-facing address of the frontend so the QR code works from customers' phones (not `localhost`).

---

## Observability (Dash0)

ByteOrder is instrumented with OpenTelemetry. If you have the [Dash0 operator](https://github.com/dash0hq/dash0-operator) installed in your cluster:

```bash
helm upgrade byteorder deploy/helm/byteorder \
  -n byteorder --reuse-values --set dash0.enabled=true
```

For docker-compose, set `OTEL_ENDPOINT` in your `.env`:

```env
OTEL_ENDPOINT=http://your-otel-collector:4317
```

---

## Environment variables reference

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | admin, menu, order, print | Full PostgreSQL DSN |
| `REDIS_URL` | order, print | Redis URL (default `redis://redis:6379`) |
| `JWT_SECRET` | admin | Secret for signing JWTs — must be strong in production |
| `ADMIN_DEFAULT_PASSWORD` | admin | Password for the `admin` user created on first run |
| `MENU_SERVICE_URL` | admin | Internal URL of menu-service |
| `ORDER_SERVICE_URL` | admin | Internal URL of order-service |
| `OTEL_ENDPOINT` | all | OpenTelemetry collector gRPC endpoint (optional) |

---

## Building from source

```bash
# Build all images
cd deploy
docker compose build

# Or build individually
docker build -t byteorder/admin ./admin
docker build -t byteorder/frontend ./frontend
docker build -t byteorder/menu-service ./menu-service
docker build -t byteorder/order-service ./order-service
docker build -t byteorder/print-service ./print-service
```

Multi-arch builds (linux/amd64 + linux/arm64) are handled by GitHub Actions on every push to `main`.

---

## Contributing

Pull requests are welcome. Please open an issue first to discuss significant changes.

## Licence

Copyright © 2026 Matthew Wallace

Released under the [GNU Affero General Public License v3.0](LICENSE).

You are free to use, modify, and self-host this software. If you offer it as a hosted or managed service, the AGPL requires you to make any modifications publicly available under the same licence.

For commercial licensing enquiries (e.g. running a managed service without AGPL obligations), please open an issue or get in touch directly.
