# IQA MobileNetV2 Experiment Summary

## Dataset

- Dataset: WoodScape fisheye soiling dataset
- Task: binary classification
- Classes: normal, soiling
- Split strategy: stratified 70% train / 15% validation / 15% test with seed `42`

| Split | Class | Count | Valid Images |
|---|---|---:|---:|
| train | normal | 5764 | 5764 |
| train | soiling | 3500 | 3500 |
| val | normal | 1235 | 1235 |
| val | soiling | 750 | 750 |
| test | normal | 1235 | 1235 |
| test | soiling | 750 | 750 |

## Model

- Backbone: MobileNetV2
- Pretrained weights: official ImageNet pretrained weights from Torchvision
- Classifier: 2-class linear classification head

## Training Setup

- Image size: 224 x 224
- Optimizer: AdamW
- Scheduler: Cosine learning rate scheduler
- Epochs configured: 200
- Epochs completed: 6
- Batch size: 128
- Best validation F1: 1.0000

## Test Results

| Metric | Value |
|---|---:|
| Test Loss | 0.0096 |
| Accuracy | 0.9985 |
| Precision | 0.9987 |
| Recall | 0.9973 |
| F1 Score | 0.9980 |
| AUC | 1.0000 |

## Output Figures

- Training curves: `outputs/iqa_mobilenetv2/figures/training_curves.png`
- Confusion matrix: `outputs/iqa_mobilenetv2/figures/confusion_matrix.png`
- Qualitative inference samples: `outputs/iqa_mobilenetv2/figures/qualitative_iqa_samples.png`

## Artifacts

- Best checkpoint: `outputs/iqa_mobilenetv2/checkpoints/best.pt`
- Last checkpoint: `outputs/iqa_mobilenetv2/checkpoints/last.pt`
- TorchScript: `outputs/iqa_mobilenetv2/checkpoints/iqa_mobilenetv2_torchscript.pt`
- ONNX: `outputs/iqa_mobilenetv2/checkpoints/iqa_mobilenetv2.onnx`
- Test predictions: `outputs/iqa_mobilenetv2/metrics/test_predictions.csv`

## Notes

The reproduced result may differ from the report because of dataset version, split strategy, preprocessing, augmentation, random seed, and hardware environment.
