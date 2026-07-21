find src/ scripts/ Makefile -type f -exec awk 'FNR==1{print "\n--- FILE: "FILENAME" ---"}1' {} + > audit_bundle.txt
