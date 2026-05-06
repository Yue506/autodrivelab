# IQA MobileNetV2 Experiment Summary

## Dataset

- Dataset: WoodScape fisheye soiling dataset
- Task: binary classification
- Classes: normal, soiling
- Data root: `data/woodscape_iqa`

## Model

- Backbone: MobileNetV2
- Pretrained weights: official ImageNet pretrained weights from Torchvision
- Classifier: 2-class linear classification head

## Training Setup

- Image size: 224 x 224
- Optimizer: AdamW
- Scheduler: Cosine learning rate scheduler
- Epochs: 200
- Batch size: 64

## Test Results

Pending execution. Results will be read from `outputs/iqa_mobilenetv2/metrics/test_metrics.json` after training and evaluation.

| Metric | Value |
|---|---:|
| Test Loss | pending |
| Accuracy | pending |
| Precision | pending |
| Recall | pending |
| F1 Score | pending |
| AUC | pending |

## Output Figures

- Training curves
- Confusion matrix
- Qualitative inference samples

## Notes

The reproduced result may differ from the report because of dataset version, split strategy, preprocessing, augmentation, random seed, and hardware environment.
