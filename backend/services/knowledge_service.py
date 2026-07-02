from knowledge.medical_knowledge import MEDICAL_KNOWLEDGE


def retrieve_knowledge(findings):

    knowledge = []

    for finding in findings:

        parameter = finding["parameter"]
        status = finding["calculated_status"]

        if parameter in MEDICAL_KNOWLEDGE:

            if status in MEDICAL_KNOWLEDGE[parameter]:

                knowledge.append({

                    "parameter": parameter,

                    "status": status,

                    "details": MEDICAL_KNOWLEDGE[parameter][status]

                })

    return knowledge