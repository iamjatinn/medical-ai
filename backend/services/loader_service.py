import os
import logging

logger = logging.getLogger(__name__)


def load_documents(folder_path):

    logger.info("Loading medical documents.")

    documents = []

    for filename in os.listdir(folder_path):

        if filename.endswith(".txt"):

            file_path = os.path.join(
                folder_path,
                filename
            )

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                documents.append(
                    file.read()
                )

    logger.info(
        f"{len(documents)} documents loaded."
    )

    return documents