# Synthetic demo data

Use only synthetic/fabricated documents for the demo. Do not place real Aadhaar, passport, visa, bank or other sensitive identity documents in this folder.

Recommended dataset structure for future model training:
data/
  train/
    genuine/
    tampered/
  validation/
    genuine/
    tampered/

For each tampered sample, record the manipulation type:
- photo replacement
- text replacement
- date alteration
- copy-paste
- stamp/signature manipulation
- background replacement
- recompression
