---
layout: default
title: Quick Start
nav_order: 3
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

<span class="big-text">Quick Start Guide</span><br/><span class="med-text">Community Edition</span>

---

## 1. Prerequisites  

- To run SWIRL in Docker, you must have the latest **[Docker app](https://docs.docker.com/get-docker/)** installed for **macOS, Linux, or Windows**.  
- **Windows users:** You must first install and configure **WSL 2** or **Hyper-V**, as outlined in the **[Docker Desktop system requirements](https://docs.docker.com/desktop/install/windows-install/#system-requirements)**.  

{: .warning }  
**Ensure that the Docker app is running before proceeding!**  

## 2. Download and Start SWIRL  

1. **Download the Docker Compose file**  

    ```shell
    curl https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml -o docker-compose.yaml
    ```

2. **Set Up Environment Variables**  

    To enable **Real-Time Retrieval-Augmented Generation (RAG)** in SWIRL, you must export the following environment variables.
    
    **MSAL values for SWIRL's host and port**

    *MacOS or Linux:*
    ```shell
    export MSAL_CB_PORT=8000
    export MSAL_HOST=localhost
    ```

    *Windows (PowerShell):*
    ```powershell
    $Env:MSAL_CB_PORT = "8000"
    $Env:MSAL_HOST = "localhost"
    ```

    **Valid model version along with valid OpenAI or Azure/OpenAI credentials**

    *MacOS or Linux:*
    ```shell
    export SWIRL_RAG_MODEL='gpt-4.1'

    export OPENAI_API_KEY=<your-OpenAI-API-key>

    export AZURE_OPENAI_KEY=<your-AzureOpenAI-key>
    export AZURE_OPENAI_ENDPOINT=<your-AzureOpenAI-endpoint>
    export AZURE_MODEL='gpt-4.1'
    export AZURE_API_VERSION=<your-AzureOpenAI-version>
    ```

    *Windows (PowerShell):*
    ```powershell
    $Env:SWIRL_RAG_MODEL = "gpt-4.1"

    $Env:OPENAI_API_KEY = "<your-OpenAI-API-key>"

    $Env:AZURE_OPENAI_KEY = "<your-AzureOpenAI-key>"
    $Env:AZURE_OPENAI_ENDPOINT = "<your-AzureOpenAI-endpoint>"
    $Env:AZURE_MODEL = "gpt-4.1"
    $Env:AZURE_API_VERSION = "<your-AzureOpenAI-version>"
    ```

3. **Start SWIRL**  

    **For macOS or Linux:**  
    ```shell
    docker compose pull && docker compose up
    ```

    **For Windows (PowerShell):**  
    ```powershell
    docker compose up
    ```

    After a few minutes, you should see output similar to:  

    ```shell
    app-1    | Start: celery-worker -> celery -A swirl_server worker ... Ok, pid: 55
    app-1    | INFO 2025-02-17 15:45:00 server Listening on TCP address 0.0.0.0:8000
    ```

## 3. Access the SWIRL Interface  

- Open **[http://localhost:8000](http://localhost:8000)** (or **[http://localhost:8000/galaxy](http://localhost:8000/galaxy)**) in your browser.  
- If the search page appears, **click `Log Out`** at the top-right corner. The SWIRL login page will load:  

<img src="images/swirl_40_login.png" alt="SWIRL 4.0 Login" width="300">  

- **Login credentials:**  
  - **Username:** `admin`  
  - **Password:** `password`  

- Enter a search query in the search box and click `Search`. Ranked results should appear within a few seconds:  

![SWIRL AI Search 4.0 Results](images/swirl_40_results.png)  

## 4. Generate AI Insights  

- Click the `Generate AI Insight` button to apply **Retrieval-Augmented Generation (RAG)** using the most relevant results.  

{: .warning }  
**Important:** If using the **Community Edition**, you *must* set up **OpenAI** or **Azure OpenAI** before running this step.

![SWIRL AI Search 4.0 Results with RAG](images/swirl_40_community_rag.png)  

## 5. Managing SWIRL  

- Click the **profile avatar** in the upper-right corner of the **Galaxy UI**.  
- Select **[Manage SWIRL](http://localhost:8000/swirl/)** to explore additional features.  
- To view raw search results in JSON format:
  - Go to **[http://localhost:8000/swirl/search/](http://localhost:8000/swirl/search/)**
  - Click on the `result_url` link to view the full JSON response.

![SWIRL JSON response](images/swirl_results_mixed_1.png)  

## 6. Shutting Down SWIRL  

You can stop SWIRL in several ways:

1. **Using Docker Desktop:**  
   ![Shutdown SWIRL with Docker Desktop](images/shutdown_docker.png)  

2. **Using Terminal (CTRL+C):**  
   ![Shutdown SWIRL with Control-C](images/shutdown_ctl_c.png)  

3. **Using Docker Compose (from a new terminal window):**  
   ```shell
   docker compose stop
   ```
   ![Shutdown SWIRL with docker compose](images/shutdown_compose.png)  

{: .warning }  
The **Docker version** of SWIRL AI Search Community Edition does *not* retain any data or configuration when shut down.

---

## Notes

{: .highlight }  
**Pre-configured SearchProviders**
SWIRL includes **active SearchProviders** for:  
✅ **Arxiv.org**  
✅ **European PMC**  
✅ **Google News**  
These work **out of the box** as long as internet access is available.  

{: .highlight } 
SWIRL includes **inactive SearchProviders** for:  
🔹 **Google Web**  
🔹 **SWIRL Documentation**  
These require a **Google API key**. See the [SearchProvider Guide](./SP-Guide#activating-a-google-programmable-search-engine-pse-searchprovider) for setup instructions.

{: .highlight }  
**Using SWIRL with Microsoft 365 requires installation and approval by an authorized company administrator**.  
For more details, refer to the **[M365 Guide](./M365-Guide)** or contact support.
