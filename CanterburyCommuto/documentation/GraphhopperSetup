## Self-Hosting GraphHopper (Java 17, macOS & Windows Setup Guide)

This guide provides instructions to install Java 17 and set up GraphHopper for local use on macOS (M1/M2/M3) and Windows systems.

### 1. Download and Install Java 17 (Required to Self-Host GraphHopper)

#### Windows

1. Go to: https://adoptium.net/temurin/releases/?version=17  
2. Download the `.msi` installer for **Windows x64** (Temurin 17 - LTS)  
3. Run the installer and complete the installation

#### macOS (M1/M2/M3)

1. Go to: https://adoptium.net/temurin/releases/?version=17  
2. Select:
   - OS: `macOS`
   - Architecture: `aarch64`
   - Version: `17 - LTS`
3. Download the `.pkg` installer (Temurin 17)  
4. Run the installer and complete the setup

### 2. Set Up and Run GraphHopper Locally

#### 2.a Setup on macOS

#### 2.a.1 Check if Homebrew is installed (needed for `wget`)

Open Terminal and run:

```bash
brew --version
```

If Homebrew is not installed, install it with:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

#### 2.a.2 Install `wget` using Homebrew

```bash
brew install wget
```

---

#### 2.a.3 Create a project folder for GraphHopper

```bash
cd ~
mkdir graphhopper_local
cd graphhopper_local
```

---

#### 2.a.4 Download required files into the folder

GraphHopper JAR:

```bash
wget https://repo1.maven.org/maven2/com/graphhopper/graphhopper-web/10.0/graphhopper-web-10.0.jar
```

Configuration file:

```bash
wget https://raw.githubusercontent.com/graphhopper/graphhopper/10.x/config-example.yml
```

Côte d'Ivoire map file:

```bash
wget https://download.geofabrik.de/africa/ivory-coast-latest.osm.pbf
```

---

#### 2.a.5 Confirm all files were downloaded

```bash
ls -lh
```

You should see the following files:

- `graphhopper-web-10.0.jar`
- `config-example.yml`
- `ivory-coast-latest.osm.pbf`

---

#### 2.a.6 Start the local GraphHopper server

Run this from inside the `graphhopper_local` folder:

```bash
java -Ddw.graphhopper.datareader.file=ivory-coast-latest.osm.pbf \
     -jar graphhopper-web-10.0.jar server config-example.yml
```

Once running, open in your browser:

```
http://localhost:8989
```

---

#### Notes (macOS)

- First launch builds the graph (takes a few minutes)
- Leave the Terminal window open while server is running
- Stop with `Control + C`
- Java must remain installed
- Git is not required

#### 2.b Setup on Windows

#### 2.b.1 Open PowerShell and create a working directory

```powershell
mkdir $HOME\graphhopper_local
cd $HOME\graphhopper_local
```

---

#### 2.b.2 Download required files using PowerShell

```powershell
Invoke-WebRequest https://repo1.maven.org/maven2/com/graphhopper/graphhopper-web/10.0/graphhopper-web-10.0.jar -OutFile graphhopper-web-10.0.jar

Invoke-WebRequest https://raw.githubusercontent.com/graphhopper/graphhopper/10.x/config-example.yml -OutFile config-example.yml

Invoke-WebRequest https://download.geofabrik.de/africa/ivory-coast-latest.osm.pbf -OutFile ivory-coast-latest.osm.pbf
```

---

#### 2.b.3 Confirm files are present

```powershell
dir
```

You should see the following files:

- `graphhopper-web-10.0.jar`
- `config-example.yml`
- `ivory-coast-latest.osm.pbf`

---

#### 2.b.4 Run the GraphHopper server

```powershell
java "-Ddw.graphhopper.datareader.file=ivory-coast-latest.osm.pbf" -jar graphhopper-web-10.0.jar server config-example.yml
```

---

#### 2.b.5 Open in your browser

```
http://localhost:8989
```

---

#### Notes (Windows)

- First run will build the graph (can take several minutes)
- The PowerShell window must remain open while the server runs
- Stop the server with `Control + C`
- Java must remain installed
- Git is not required

#### 2.c Restarting GraphHopper After Initial Setup (macOS and Windows)

If you've already downloaded the map and run GraphHopper at least once, you do **not** need to rebuild the graph each time. You can simply restart the server using the same command from the project folder.

---

#### macOS

1. Open **Terminal**
2. Navigate to your GraphHopper directory:

```bash
cd ~/graphhopper_local
```

3. Start the server:

```bash
java -Ddw.graphhopper.datareader.file=ivory-coast-latest.osm.pbf \
     -jar graphhopper-web-10.0.jar server config-example.yml
```

4. Open your browser and go to:

```
http://localhost:8989
```

---

#### Windows

1. Open **PowerShell**
2. Navigate to your GraphHopper directory:

```powershell
cd $HOME\graphhopper_local
```

3. Start the server:

```powershell
java "-Ddw.graphhopper.datareader.file=ivory-coast-latest.osm.pbf" -jar graphhopper-web-10.0.jar server config-example.yml
```

4. Open your browser and go to:

```
http://localhost:8989
```

---

#### Notes

- You only need to rebuild the graph if you change the map file or delete the existing graph data.
- The server must stay running while you use the local GraphHopper web interface.



