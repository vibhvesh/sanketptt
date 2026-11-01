#!/bin/bash
# usage: build.sh <package> "<App Name>" <url> <#color> <out.apk>   (needs JDK17 + build-tools 34 + android-34)
set -e; SDK=${ANDROID_HOME:-/opt/android}; BT=$SDK/build-tools/34.0.0; JAR=$SDK/platforms/android-34/android.jar
D=$(dirname "$(readlink -f "$0")"); T=$(mktemp -d); P=$1
mkdir -p $T/res/drawable $T/java/${P//.//} $T/obj $T/dex
sed "s/PKG/$P/;s|APPNAME|$2|" $D/src/AndroidManifest.xml > $T/AndroidManifest.xml
sed "s/COLOR/$4/" $D/src/ic.xml > $T/res/drawable/ic.xml
sed "s/PKG/$P/;s|APPURL|$3|" $D/src/MainActivity.java > $T/java/${P//.//}/MainActivity.java
$BT/aapt2 compile --dir $T/res -o $T/res.zip
$BT/aapt2 link -I $JAR --manifest $T/AndroidManifest.xml -o $T/u.apk $T/res.zip
javac -source 8 -target 8 -nowarn -cp $JAR -d $T/obj $(find $T/java -name '*.java') 2>&1 | grep -v warning || true
$BT/d8 --release --min-api 24 --lib $JAR --output $T/dex $(find $T/obj -name '*.class')
(cd $T/dex && jar uf $T/u.apk classes.dex)
$BT/zipalign -f 4 $T/u.apk $T/a.apk
KS=${KEYSTORE:-$D/sanket.keystore}; [ -f $KS ] || keytool -genkeypair -keystore $KS -storepass sanket123 -keypass sanket123 -alias sanket -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Sanket" >/dev/null 2>&1
$BT/apksigner sign --ks $KS --ks-pass pass:sanket123 --out $5 $T/a.apk; rm -rf $T
