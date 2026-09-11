# Vision Model Evaluation Report

- **Model Status**: `EXPERIMENTAL`
- **Field Validation Required**: `YES`
- **Model Checksum**: `04f991d4e430859f81f37303f023718197481709cba2e4234fcb3288f19be1ab`
- **Dataset**: PlantDoc (~2,600 images)
- **Split**: {"train": 1779, "val": 370, "test": 409}
- **Leakage Check**: PASSED

## Test Set Metrics

| Metric | Value |
|--------|-------|
| Overall Accuracy | 0.1443 |
| Macro F1-Score | 0.0939 |
| Weighted F1-Score | 0.105 |

## Per-Class Breakdown

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
| Apple Scab Leaf | 0.100 | 0.067 | 0.080 | 15.0 |
| Apple leaf | 0.182 | 0.133 | 0.154 | 15.0 |
| Apple rust leaf | 0.000 | 0.000 | 0.000 | 14.0 |
| Bell_pepper leaf | 0.000 | 0.000 | 0.000 | 10.0 |
| Bell_pepper leaf spot | 1.000 | 0.167 | 0.286 | 12.0 |
| Blueberry leaf | 0.000 | 0.000 | 0.000 | 18.0 |
| Cherry leaf | 0.000 | 0.000 | 0.000 | 10.0 |
| Corn Gray leaf spot | 0.000 | 0.000 | 0.000 | 11.0 |
| Corn leaf blight | 0.130 | 0.690 | 0.219 | 29.0 |
| Corn rust leaf | 0.000 | 0.000 | 0.000 | 18.0 |
| Peach leaf | 0.316 | 0.333 | 0.324 | 18.0 |
| Potato leaf early blight | 0.000 | 0.000 | 0.000 | 18.0 |
| Potato leaf late blight | 1.000 | 0.062 | 0.118 | 16.0 |
| Raspberry leaf | 1.000 | 0.053 | 0.100 | 19.0 |
| Soyabean leaf | 0.143 | 0.091 | 0.111 | 11.0 |
| Squash Powdery mildew leaf | 0.173 | 0.450 | 0.250 | 20.0 |
| Strawberry leaf | 0.200 | 0.200 | 0.200 | 15.0 |
| Tomato Early blight leaf | 0.133 | 0.143 | 0.138 | 14.0 |
| Tomato Septoria leaf spot | 0.132 | 0.304 | 0.184 | 23.0 |
| Tomato leaf | 0.000 | 0.000 | 0.000 | 10.0 |
| Tomato leaf bacterial spot | 0.100 | 0.059 | 0.074 | 17.0 |
| Tomato leaf late blight | 0.062 | 0.056 | 0.059 | 18.0 |
| Tomato leaf mosaic virus | 0.200 | 0.111 | 0.143 | 9.0 |
| Tomato leaf yellow virus | 0.000 | 0.000 | 0.000 | 12.0 |
| Tomato mold leaf | 0.000 | 0.000 | 0.000 | 15.0 |
| grape leaf | 0.100 | 0.091 | 0.095 | 11.0 |
| grape leaf black rot | 0.000 | 0.000 | 0.000 | 11.0 |


## Reproduction Command

```powershell
python -m mlbackend.training.train_vision
```

> [!WARNING]
> This model is currently in status `EXPERIMENTAL`. It has NOT been certified on farm cameras under unconstrained sunlight.
