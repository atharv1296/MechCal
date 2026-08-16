# Atlas Copco Engineering Calculator

A web-based engineering calculator platform designed to perform and track industrial calculations with precision, consistency, and traceability.

---

## Overview

The Atlas Copco Engineering Calculator is a structured toolset that enables users to:

* Perform domain-specific engineering calculations
* Store and review historical computation data
* Maintain an audit trail of all operations
* Access a clean, intuitive interface for technical workflows

---

## Features

### Calculation Engine

* Multiple engineering calculators
* Structured input/output handling
* Accurate and consistent computation logic

### History & Audit Trail

* Persistent storage of all calculations
* Timestamped records
* Clear separation of inputs and outputs
* Easy navigation back to calculators

### User Interface

* Clean, responsive design
* Table-based history visualization
* Data pills for structured parameter display


## Technologies Used

* Backend: Flask (Python)
* Frontend: HTML, CSS, Jinja2
* Styling: Custom CSS with variables
* Icons: Lucide Icons
* Data Handling: JSON-based input/output storage

---

## Pages

### Home

* Entry point for all calculators

### History

* Displays all past calculations
* Includes:

  * Calculation ID
  * Tool used
  * Inputs and outputs
  * Timestamp

### About

* Describes platform purpose and capabilities
* Includes system and project information

---

## Data Handling

* Inputs and outputs are stored as JSON
* Parsed dynamically in templates
* Rendered as structured UI elements

---

## Key Design Principles

* Clarity over complexity
* Engineering-focused UX
* Scalable component structure
* Separation of concerns (logic vs presentation)

---

## Usage

1. Select a calculator from the homepage
2. Enter required input parameters
3. Execute calculation
4. View results instantly
5. Access saved records in the History page

---

## Database & Cloudinary Configuration

The platform supports **Neon PostgreSQL** for production relational data storage and **Cloudinary** for persistent cloud asset/image hosting.

### Required Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# 1. Neon PostgreSQL Connection String
DATABASE_URL=postgresql://<user>:<password>@<neon_host>.neon.tech/<dbname>?sslmode=require

# 2. Cloudinary Connection URL
CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>

# 3. Security
SECRET_KEY=your_production_secret_key
```

### Data Migration (SQLite to Neon PostgreSQL)

To safely copy existing users, calculators, and calculations from your local SQLite database (`instance/calculators.db`) to Neon PostgreSQL and sync local reference images to Cloudinary, run:

```bash
python migrate_data.py
```

*Note: The migration script is 100% idempotent and can be safely re-run without creating duplicate records.*

---

## Deployment on Render

1. Connect your repository to Render.
2. In your Render Dashboard, add the following **Environment Variables**:
   * `DATABASE_URL`: Your Neon PostgreSQL connection string.
   * `CLOUDINARY_URL`: Your Cloudinary API connection string.
   * `SECRET_KEY`: A secure random string.
3. Deploy! Render will install dependencies from `requirements.txt` and start with Gunicorn.

