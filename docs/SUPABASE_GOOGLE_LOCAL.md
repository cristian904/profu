# Enable Google Sign-In for Local Supabase

The app uses **local Supabase** (`http://127.0.0.1:54321`). The "provider is not enabled" error means Google must be enabled in **config.toml** (the hosted dashboard does not apply to local).

## 1. Ensure you have a `supabase` folder

From the **repo root** (`d:\_CRISTIAN\profu`):

```bash
npx supabase init
```

This creates `supabase/config.toml` if it doesn't exist. The `supabase/` folder is in `.gitignore`, so it won't appear in version control.

## 2. Get Google OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**.
2. Create an **OAuth 2.0 Client ID** (type: **Web application**).
3. Under **Authorized redirect URIs** add:
   - `http://127.0.0.1:54321/auth/v1/callback`
   - If you use a different port for the Flutter app, still use `54321` here (that’s the Supabase Auth port).
4. Copy the **Client ID** and **Client secret**.

## 3. Edit `supabase/config.toml`

Open **supabase/config.toml** and find the `[auth.external.google]` section. If it doesn’t exist, add it.

Set it to:

```toml
[auth.external.google]
enabled = true
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
secret = "YOUR_CLIENT_SECRET"
redirect_uri = ""
```

Replace `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` with your real values.

**Optional (use env vars):** Create a `.env` file in the **repo root** (do not commit it):

```
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
```

Then in `config.toml`:

```toml
[auth.external.google]
enabled = true
client_id = "env(GOOGLE_CLIENT_ID)"
secret = "env(GOOGLE_CLIENT_SECRET)"
redirect_uri = ""
```

## 4. Restart local Supabase

After changing `config.toml` you must restart:

```bash
npx supabase stop
npx supabase start
```

## 5. Redirect URL for the Flutter app (web)

In Supabase Dashboard (or for local, in **Auth** settings) add your app URL to **Redirect URLs**, e.g.:

- `http://localhost:7357/` (if you run Flutter with `--web-port 7357`)

For **local** Supabase there is no dashboard; the redirect is handled by Auth. Just ensure your Flutter app’s `redirectTo` matches the URL you use in the browser (e.g. `http://localhost:7357/`).

## Checklist

- [ ] `supabase/config.toml` has `[auth.external.google]` with `enabled = true`, `client_id`, and `secret`.
- [ ] Google Cloud OAuth client has redirect URI `http://127.0.0.1:54321/auth/v1/callback`.
- [ ] You ran `npx supabase stop` then `npx supabase start` after editing config.
- [ ] No typos in `client_id` (e.g. `.apps.googleusercontent.com` at the end).

After this, "Sign in with Google" on the login page should stop returning "provider is not enabled".
