#!/bin/bash
# Masaustune "Oddsy Bot" kisayolu (alias) koyar.
cd "$(dirname "$0")" || exit 1
HEDEF="$(pwd)/BOTU_CALISTIR.command"
MASAUSTU="$HOME/Desktop"

echo
if [ ! -d "$MASAUSTU" ]; then
    echo "  HATA: Masaustu klasoru bulunamadi: $MASAUSTU"
    echo
    read -n 1 -s -r -p "  Kapatmak icin bir tusa bas..."
    exit 1
fi

chmod +x "$HEDEF"
ln -sfn "$HEDEF" "$MASAUSTU/Oddsy Bot.command"

echo "  Tamam. Masaustunde \"Oddsy Bot\" olustu."
echo "  Cift tiklayinca bot calisir."
echo
echo "  NOT: Ilk acilista macOS \"gelistirici dogrulanamadi\" diyebilir."
echo "       Sag tikla > Ac > Ac dersen bir daha sormaz."
echo
read -n 1 -s -r -p "  Kapatmak icin bir tusa bas..."
echo
