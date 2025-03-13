---
layout: default
title: Quick Start
nav_order: 7
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

<span class="big-text">Quick Start Guide</span><br/><span class="med-text">Enterprise Edition</span>

{: .warning }
Please [contact SWIRL](mailto:hello@swirlaiconnect.com) for access to SWIRL Enterprise.

{: .highlight }
Please note: we've renamed our products! **SWIRL AI Connect** is now **SWIRL AI Search** 🔎 and **SWIRL AI Co-Pilot** is now **SWIRL AI Search Assistant** 🤖

---

* The recommended minimum system configuration is a **16-core server**, with **32 GB of memory** and at least **500 GB of available disk space**. This configuration supports up to **25 users**.

* To run SWIRL in Docker, install the latest version of [Docker](https://docs.docker.com/get-docker/) for macOS, Linux, or Windows. **Ensure Docker is configured to use all available CPU, memory, and storage.**

* You must be logged in to Docker Hub. Open a command-line interface (CLI) and execute the following command, replacing `<docker-username>` and `<docker-password>` with your credentials:

```shell
docker login --username <docker-username> --password <docker-password>
```

* **Windows users** must install and configure either **WSL 2** or the **Hyper-V backend**, as outlined in the [Docker Desktop System Requirements](https://docs.docker.com/desktop/install/windows-install/#system-requirements).

{: .warning }
Ensure Docker is running before proceeding!

## Downloading SWIRL Enterprise Files

1. Locate the email with the subject **"Try SWIRL Enterprise"**.
2. The email contains three attachments:
   - A PDF with detailed instructions
   - `docker-compose.yaml`
   - `env.license`
3. **Save** `docker-compose.yaml` to a folder on the target server.
4. **Rename** `env.license` to `.env.license` and save it in the same folder.

{: .warning }
The leading dot (`.`) in `.env.license` is required!

## Starting SWIRL Enterprise

1. Open a command line and navigate to the folder where `docker-compose.yml` is saved.
2. Run the following command to pull and start the containers:

```shell
docker-compose pull && docker-compose up
```

This starts all services required by SWIRL. Initialization takes a few minutes.

{: .warning }
Do not press `CTRL+C` or stop Docker during this process—doing so will shut down SWIRL.

Once complete, the output should look like this: 

![SWIRL Enterprise Docker successful startup](images/swirl_enterprise_docker_started.png)

## Verifying SWIRL Startup

1. Open a new command line and check the running containers:

    ```shell
    docker ps
    ```

    The output should look like this:
    ![SWIRL Enterprise Docker ps command](images/swirl_docker_ps.png)

2. Open a browser and navigate to <http://localhost:8000> or <http://localhost:8000/galaxy>  

3. If the search page loads, click `Log Out` in the top-right corner. The login page will appear:

    ![SWIRL Login](images/swirl_40_login.png)

4. Log in with:

   - **Username:** `admin`  
   - **Password:** `password`  

   {: .warning }
   If you receive a warning about the password being compromised, follow these steps:  
   [Change the super user password](./Admin-Guide#changing-the-super-user-password)

5. Enter a search term and press `Search`. The ranked results should appear:

    ![SWIRL Results No M365](images/swirl_40_results.png)

    If no results appear or an error occurs, please [contact support](#support).

## Enabling AI Features

{: .warning }
To use **Generate AI Insights** (RAG) or **AI Search Assistant**, at least one AI provider must be activated.

1. Go to [http://localhost:8000/swirl/aiproviders/](http://localhost:8000/swirl/aiproviders/).
2. Review the **pre-loaded AI providers**.
3. To edit a provider, add its ID to the URL. Example: <http://localhost:8000/swirl/aiproviders/16/>

    ![SWIRL AI Provider](images/swirl_aip_1.png)

4. Use the **"Raw Data"** form at the bottom to make changes, then click **PUT** to save.

    To function correctly, an AI provider must:

    - Have `"active": true` set.
    - Include `"rag"` and/or `"chat"` in the `"tags"` list.
    - Include `"rag"` and/or `"chat"` in the `"default"` list.
    - Have a valid API key (if required).

5. To create a new provider, **copy an existing one** and paste it as a new entry.

    To use **different AI providers** for **RAG and AI Search Assistant**, adjust the `"defaults"` list:

    - Example:  
      - **OpenAI GPT-4** → `"defaults": ["rag"]`
      - **Azure/OpenAI GPT-4o** → `"defaults": ["chat"]`

6. Once an active provider for **RAG** exists, click **Generate AI Insights**.

    ![SWIRL Results with RAG](images/swirl_40_community_rag.png)

7. To access **SWIRL AI Search Assistant**, visit: [http://localhost:8000/galaxy/chat](http://localhost:8000/galaxy/chat)

8. Ask a question, such as "Tell me about SWIRL AI Connect?"

    ![SWIRL Assistant Conversation with RAG Result](images/swirl_40_enterprise_assistant_rag.png)

## Stopping SWIRL

To stop SWIRL, use one of these methods:

1. **Via Docker Desktop:**
   ![Shutdown SWIRL with Docker Desktop](images/shutdown_docker.png)

2. **Using CTRL-C in the terminal:**
   ![Shutdown SWIRL with Control-C](images/shutdown_ctl_c.png)

3. **Via a separate terminal:**

```shell
docker-compose stop
```

   ![Shutdown SWIRL with docker compose](images/shutdown_compose.png)

These methods **preserve** the SWIRL database. If you don't need to save data, press `CTRL-C` **twice** to stop SWIRL instantly.

## Optional Steps

- Manage SWIRL via **Galaxy UI**:
  - Click the profile avatar (top-right corner).
  - Click **Manage SWIRL** ([http://localhost:8000/swirl/](http://localhost:8000/swirl/)).

## Microsoft 365 Integration

To connect SWIRL with **Microsoft 365**, you need:

- **Admin access** to the Azure/M365 tenant.
- **App registration** in Azure.
- **App ID and secrets** added to SWIRL.

Setup takes ~1 hour. Follow the guide: [Microsoft 365 Integration Guide](./M365-Guide)

For additional support, please [contact SWIRL](#support).

## Persisting Configuration Changes

1. Identify your SWIRL Docker container (`app` in the name):

   ![SWIRL docker container app name](images/persist_1.png)

2. Copy the `.env` file outside Docker:

   ![SWIRL container env](images/persist_env1.png)

3. Stop the containers:

   ![SWIRL containers stop](images/persist_stop.png)

4. Modify `docker-compose.yml`:

   **Before:**  
   ![SWIRL config before](images/persist_before.png)

   **After:**  
   ![SWIRL config after](images/persist_after.png)

5. Restart SWIRL:

```shell
docker-compose pull && docker-compose up
```