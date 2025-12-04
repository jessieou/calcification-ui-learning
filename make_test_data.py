import csv
from datetime import datetime

filename = "output/yjo_learning.csv"   

with open(filename, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "userID", "timestamp", "case_id",
        "patient_id", "pathology", "birads", "confidence"
    ])

    for i in range(1, 241):  # 1 through 240
        writer.writerow([
            "yjo",
            datetime.now().isoformat(),
            i,               # case_id
            i,               # fake patient_id
            "Benign",        # dummy pathology
            "BI-RADS 2",     # dummy birads
            "50%"            # dummy confidence
        ])
