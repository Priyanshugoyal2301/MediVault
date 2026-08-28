# Developer guide — Image quality

1. Default `USE_IMAGE_QUALITY_MODEL=0` (passthrough).  
2. Train: `python models/image_quality/train.py`  
3. Eval: `python models/image_quality/evaluate.py`  
4. Optional: `pip install torch torchvision pypdfium2`  
5. Pixel CNN train: `IMAGE_QUALITY_TRAIN_PIXELS=1`  
6. Smoke: flag on → `get_quality_checker().check(png_bytes, "image/png")`  
7. Poor quality → `/parse` returns empty values (existing behavior).
