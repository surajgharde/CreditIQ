# Render Deployment Guide for Vivriti (FastAPI Backend + React/Vite Frontend)

This guide takes you through deploying the Vivriti project on Render. Render is an excellent platform for hackathons as it offers a free tier for both web services (your Python backend) and static sites (your React app).

## 1. Preparation
1. **GitHub Account**: Make sure your local codebase is committed and pushed up to a GitHub repository.
2. **Render Account**: Go to [Render.com](https://render.com) and sign up using your GitHub account.

---

## 2. Deploying the Backend (FastAPI Web Service)

Since the backend is built with FastAPI and Python, we will deploy it as a Render **Web Service**.

### Step 2.1: Create a New Web Service
1. On your Render dashboard, click **New +** and select **Web Service**.
2. Connect your GitHub account and authorize Render to see your repositories, then select the **Vivriti** repository.

### Step 2.2: Configure the Backend Service
Fill in the configuration details as follows:
- **Name**: `vivriti-backend` (or a name of your choice)
- **Region**: Choose the region closest to your primary users.
- **Branch**: `main` (or whichever branch holds your production code)
- **Root Directory**: `backend` *(This is absolutely crucial—it tells Render to look inside the backend folder for commands and dependencies!)*
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 2.3: Environment Variables & Database
Scroll down to **Environment Variables** and add any keys from your local `d:\TGP\Vivriti\.env` file that your backend requires to function:
- Add your API Keys (`OPENAI_API_KEY`, etc. if you are using AI integrations).
- **Important Database Note (SQLite vs PostgreSQL)**: If you are currently using `creditiq.db` (SQLite), Render will delete this SQLite database file every time the backend is restarted or redeployed due to their ephemeral disk policy on free tiers. 
  - *Fix for Hackathons:* If data persistence isn't your primary concern, SQLite is fine. 
  - *Fix for Persistence:* Before creating the Web Service, deploy a free **PostgreSQL Database** on Render, copy its "Internal Database URL", and set it as an environment variable (e.g., `DATABASE_URL`) on your backend.

### Step 2.4: Deploy
Click **Create Web Service**. 
1. Render will fetch your code and start the Build step (`pip install`).
2. Keep an eye on the console logs until you see `Application startup complete`.
3. Make a note of the **public URL** Render provides at the top (e.g., `https://vivriti-backend-xxxx.onrender.com`). You will need this to connect your frontend!

---

## 3. Deploying the Frontend (React + Vite Static Site)

The frontend is built via Vite and React. Since it compiles to static HTML/JS/CSS, deploying it as a Render **Static Site** is the fastest and most cost-effective method (and it has no sleep delays on the free tier).

### Step 3.1: Create a New Static Site
1. Go back to your Render Dashboard, click **New +**, and select **Static Site**.
2. Select your **Vivriti** repository again.

### Step 3.2: Configure the Frontend Service
Fill in the configuration details:
- **Name**: `vivriti-frontend`
- **Branch**: `main`
- **Root Directory**: `frontend` *(Again, crucial!)*
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist` (Vite compiles code into the `dist` folder by default).

### Step 3.3: Environment Variables for Frontend
You must tell your frontend where to find the deployed backend API (otherwise, it will try to call `localhost:8000`). Find the **Environment Variables** section:
- **Key**: `VITE_API_BASE_URL` (or whatever specific environment variable your frontend codebase uses to target the backend API).
- **Value**: The public URL of the backend you copied earlier (e.g., `https://vivriti-backend-xxxx.onrender.com`). 
> *Tip: Make sure there is no trailing slash `/` at the end of the URL unless your code specifically expects it.*

### Step 3.4: Deploy
Click **Create Static Site**. Render will run the installation and build process, then publish your static assets.

### Step 3.5: Handle React SPA Routing (Important!)
Because React is a Single Page Application, direct link navigations (like refreshing the page on `/dashboard`) can throw a 404 error on static hosts. 
To fix this:
1. In your Static Site settings on Render, navigate to the **Redirects/Rewrites** tab on the left.
2. Add a new rule with the following parameters:
   - **Source**: `/*`
   - **Destination**: `/index.html`
   - **Action**: `Rewrite`
3. Click **Save Changes**.

---

## 4. Testing Your Deployed Application

1. Open your frontend's public URL provided by Render (e.g., `https://vivriti-frontend-yyyy.onrender.com`).
2. Test the core flows: Try logging in, initiating a chat, or generating an analysis to guarantee the backend connects.
3. If an action fails, open your browser's **Developer Tools (F12)** -> **Network Tab** to ensure the API calls are succeeding (HTTP 200) and pointing exactly to your Render backend URL, not `localhost`.

---

## 5. Common Errors & Fixes During Deployment

> [!WARNING]
> **CORS Errors**
> - **Symptom**: Frontend fails to load data; browser console displays "Blocked by CORS policy."
> - **Fix**: Go to your backend's `main.py` where your FastAPI `CORSMiddleware` is set. Update the `allow_origins` array to include your Render frontend URL (e.g., `["https://vivriti-frontend-yyyy.onrender.com"]`), or set it to `["*"]` for a quick hackathon hotfix.

> [!WARNING]
> **Out of Memory during Build/Startup**
> - **Symptom**: App fails during the `pip install` step or randomly crashes with `Error 137`.
> - **Fix**: Render's free tier has a 512MB RAM maximum. Machine learning libraries (`sentence-transformers`, `scikit-learn` in your requirements) and local ML models use a lot of memory. If it crashes, you may need to reduce batch sizes, strip out unused big ML libraries, or rely on external APIs instead of local processing.

> [!WARNING]
> **Module Not Found / Directory Errors**
> - **Symptom**: UI shows "Cannot find module 'vite'" or backend shows "No such file or directory: requirements.txt".
> - **Fix**: This strictly means your **Root Directory** was left blank. Ensure it is explicitly set to `frontend` for the UI and `backend` for the web service in your platform settings.

> [!WARNING]
> **Data Loss on Restart**
> - **Symptom**: Users or generated analyses cleanly disappear when your backend wakes up from sleep.
> - **Fix**: As mentioned, this is due to using a local SQLite file (`creditiq.db`) on an ephemeral disk. To prevent this, move to an external Render PostgreSQL database, or connect a persistent cloud storage service in your `.env`.

Your application should now run smoothly in a live environment to support your hackathon demo. Good luck!
