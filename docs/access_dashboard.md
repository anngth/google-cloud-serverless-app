# Accessing the Authenticated Dashboard

Since Cloud Run requires authentication (`--no-allow-unauthenticated`), direct public hits return a `403`. Access the dashboard using one of these options:

## Option 1: gcloud Local Proxy (Recommended)
Proxy queries locally and auto-attaches active user identity headers:
```bash
gcloud run services proxy doc-processor-service --region=us-central1 --port=9091
```
* **Local Web URL**: [http://localhost:9091](http://localhost:9091)
* **Exit command**: `Ctrl+C`

## Option 2: Browser Authorization Header
Inject identity tokens using Chrome extensions (e.g. ModHeader):
1. Get token:
   ```bash
   gcloud auth print-identity-token
   ```
2. Insert Request Header:
   * **Name**: `Authorization`
   * **Value**: `Bearer <IDENTITY_TOKEN>`
3. Access Cloud Run URL directly.

## Option 3: Identity-Aware Proxy (IAP)
* Deploy **External HTTPS Load Balancer** with IAP enabled on the Backend.
* Authenticate team members using Google Workspace login policies.
