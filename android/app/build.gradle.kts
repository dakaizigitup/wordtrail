plugins { id("com.android.application") }
android {
    namespace = "org.wordtrail.ime"
    compileSdk = 35
    defaultConfig { applicationId = "org.wordtrail.ime"; minSdk = 26; targetSdk = 35; versionCode = 43; versionName = "0.1.42" }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
