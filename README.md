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

## Future Improvements

* User authentication
* Export functionality (CSV/PDF)
* Advanced analytics
* Role-based access control
* Real-time validation

