# Vertex AI RAG Agent with ADK

This repository contains a Google Agent Development Kit (ADK) implementation of a Retrieval Augmented Generation (RAG) agent using Google Cloud Vertex AI.

## Overview

The Vertex AI RAG Agent allows you to:

- Query document corpora with natural language questions
- List available document corpora
- Create new document corpora
- Add new documents to existing corpora
- Get detailed information about specific corpora
- Delete corpora when they're no longer needed

## Prerequisites

- A Google Cloud account with billing enabled
- A Google Cloud project with the Vertex AI API enabled
- Appropriate access to create and manage Vertex AI resources
- Python 3.9+ environment

## Setting Up Google Cloud Authentication

Before running the agent, you need to set up authentication with Google Cloud:

1. **Install Google Cloud CLI**:
   - Visit [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) for installation instructions for your OS

2. **Initialize the Google Cloud CLI**:
   ```bash
   gcloud init
   ```
   This will guide you through logging in and selecting your project.

3. **Set up Application Default Credentials**:
   ```bash
   gcloud auth application-default login
   ```
   This will open a browser window for authentication and store credentials in:
   `~/.config/gcloud/application_default_credentials.json`

4. **Verify Authentication**:
   ```bash
   gcloud auth list
   gcloud config list
   ```

5. **Enable Required APIs** (if not already enabled):
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

## Installation

1. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Using the Agent

The agent provides the following functionality through its tools:

### 1. Query Documents
Allows you to ask questions and get answers from your document corpus:
- Automatically retrieves relevant information from the specified corpus
- Generates informative responses based on the retrieved content

### 2. List Corpora
Shows all available document corpora in your project:
- Displays corpus names and basic information
- Helps you understand what data collections are available

### 3. Create Corpus
Create a new empty document corpus:
- Specify a custom name for your corpus
- Sets up the corpus with recommended embedding model configuration
- Prepares the corpus for document ingestion

### 4. Add New Data
Add documents to existing corpora or create new ones:
- Supports Google Drive URLs and GCS (Google Cloud Storage) paths
- Automatically creates new corpora if they don't exist

### 5. Get Corpus Information
Provides detailed information about a specific corpus:
- Shows document count, file metadata, and creation time
- Useful for understanding corpus contents and structure

### 6. Delete Corpus
Removes corpora that are no longer needed:
- Requires confirmation to prevent accidental deletion
- Permanently removes the corpus and all associated files

## Troubleshooting

If you encounter issues:

- **Authentication Problems**:
  - Run `gcloud auth application-default login` again
  - Check if your service account has the necessary permissions

- **API Errors**:
  - Ensure the Vertex AI API is enabled: `gcloud services enable aiplatform.googleapis.com`
  - Verify your project has billing enabled

- **Quota Issues**:
  - Check your Google Cloud Console for any quota limitations
  - Request quota increases if needed

- **Missing Dependencies**:
  - Ensure all requirements are installed: `pip install -r requirements.txt`

## Additional Resources

- [Vertex AI RAG Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-overview)
- [Google Agent Development Kit (ADK) Documentation](https://github.com/google/agents-framework)
- [Google Cloud Authentication Guide](https://cloud.google.com/docs/authentication)

## 🔐 Enterprise Security Architecture

This project implements a **Zero-Trust Security Architecture** designed to protect sensitive credentials and data.

### 1. Identity & Access Management (IAM)
We adhere to the **Secure Intermediary Pattern** to separate duties:

* **Agent Identity (`adk-rag-agent-sa`)**:
    * **Role**: Untrusted reasoning engine running on Cloud Run.
    * **Permissions**: Minimal. It has **NO** access to secrets, databases, or external APIs. It can only receive HTTP requests and execute basic logic.
    * **Access**: The Cloud Run service is deployed with `--no-allow-unauthenticated`, meaning it is private and can only be invoked by authorized users (e.g., admin) or frontend services with the `roles/run.invoker` permission.

* **Tool Identity (`adk-tool-sa`)**:
    * **Role**: Trusted Secure Intermediary.
    * **Permissions**: Has `roles/secretmanager.secretAccessor` to retrieve credentials at runtime.
    * **Workflow**: The Agent calls the Tool code. The Tool code uses this identity to fetch secrets *only* for the duration of the function execution. The Model/Agent never sees the raw secret.

### 2. Binary Authorization & Supply Chain Security
This service enforces strict software supply chain security using **Google Cloud Binary Authorization**:

* **Attestors**: A dedicated Attestor (`adk-rag-agent-attestor`) verifies container images.
* **Signing**: Every container image built is cryptographically signed using a **Cloud KMS** asymmetric key (`adk-rag-agent-signer`).
* **Policy**: The Cloud Run service is deployed with `--binary-authorization=default`, ensuring that only images signed by our trusted Attestor can start. Unsigned or modified images are rejected at deployment time.

### 3. Deployment Workflow
The deployment process involves a rigorous security pipeline:
1.  **Build**: Docker image is built for `linux/amd64`.
2.  **Push**: Image is pushed to Google Artifact Registry.
3.  **Sign**: The unique image digest is signed by the KMS key, creating an **Attestation**.
4.  **Deploy**: The service is deployed to Cloud Run with Binary Authorization enabled, which verifies the signature before starting the container.

## 🔧 Troubleshooting

### Common Issues

**1. "Container failed to start" / CrashLoopBackOff**
* **Cause**: Often due to missing Python dependencies in `requirements.txt`.
* **Specific Fix**: The `google-adk` library depends on the **`deprecated`** package. Ensure `deprecated` is listed in `requirements.txt`.
* **Debugging**: Run the container locally to see the exact Traceback:
    ```bash
    docker run --platform linux/amd64 -p 8080:8080 -e PORT=8080 gcr.io/YOUR_PROJECT/IMAGE:TAG
    ```

**2. "Cloud Run does not support image ... manifest type"**
* **Cause**: Building the Docker image on an Apple Silicon (M1/M2/M3) Mac creates an `arm64` image, but Cloud Run requires `amd64`.
* **Fix**: Force the platform during build:
    ```bash
    docker build --platform linux/amd64 -t IMAGE_NAME .
    ```

**3. "Constraint constraints/run.allowedBinaryAuthorizationPolicies violated"**
* **Cause**: Organization policy requires Binary Authorization.
* **Fix**: You must sign the image digest and deploy with the flag `--binary-authorization=default`.
