# Template:

```json
{
  "state": "Describe aquí la situación actual que LAYA debe evaluar.",
  "questions": {
    "pregunta_1": {
      "type": "choice",
      "instructions": "¿Qué acción debería tomar el sistema?",
      "criteria": {
        "opcion_a": "Descripción de la primera opción",
        "opcion_b": "Descripción de la segunda opción",
        "opcion_c": "Descripción de la tercera opción"
      }
    }
  }
}
```

---

# Question Types

- Choice (choice): Evaluates input against a predefined list of mutually exclusive string categories and assigns a probability distribution and confidence score across the options (e.g., routing a support ticket to billing, technical, or sales).

- Score (score): Rates the input on a zero-based, ordered (ordinal) fractional scale or defined rubric levels (e.g., measuring urgency levels such as not urgent, soon, or blocking).

- Noul (noul): Evaluates a yes/no proposition and returns a calibrated probability P(true) rather than a simple boolean flag.
