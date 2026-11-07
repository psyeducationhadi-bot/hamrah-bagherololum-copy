# Proguard rules for TWA and Android Browser Helper
-keepattributes *Annotation*
-keepclassmembers class * {
    @org.chromium.base.annotations.CalledByNative <methods>;
}
-dontwarn com.google.androidbrowserhelper.**
