# Knowledge base sources

The assistant explains lab results using the text files in `data/medical_docs/`.

## MedlinePlus (53 documents, files named `mplus_*.txt`)

- **Source:** MedlinePlus lab-test pages, a service of the **U.S. National Library of Medicine (NLM)**, https://medlineplus.gov
- **Terms:** medical-test information on MedlinePlus is a U.S. government work and is not copyrighted; MedlinePlus asks users to credit it ([terms](https://medlineplus.gov/about/using/usingcontent/)).
- **Not used:** A.D.A.M. encyclopedia articles, drug monographs and most images, which are licensed to NLM and not free to reuse.
- **How the files were made:** `tools/fetch_medlineplus.py` downloads each page politely (identifiable user-agent, 1.5 s pause, one request per page) and keeps only the article text. The "References" and "Related ..." sections are removed. The text is otherwise unchanged.
- **Per-file title, URL and download date:** `data/sources.json`.
- **Credit in the app:** every AI explanation ends with a *Sources* section listing the pages that were actually retrieved for that answer, and the credit line "MedlinePlus, National Library of Medicine".

## Project notes (6 documents)

`anemia.txt`, `diabetes.txt`, `vitamin_d.txt`, `wbc.txt`, `rbc.txt`, `platelets.txt` are short general-knowledge notes written for this project. They are not medical advice.

## Important

This content is for general education. It is **not** a diagnosis, and the app says so. A doctor should interpret any result.

To refresh or extend the knowledge base, edit the `SLUGS` list in `tools/fetch_medlineplus.py` and run it again (existing files are skipped); the search index rebuilds automatically on the next start.
