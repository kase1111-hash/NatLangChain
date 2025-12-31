# NatLangChain Quick Start Guide (Windows)

Welcome! This guide will help you get NatLangChain running on your Windows computer in just a few minutes.

## What You'll Need

Before starting, make sure you have:

- **Windows 10 or 11**
- **Python 3.9 or newer** - [Download here](https://www.python.org/downloads/)

  > ⚠️ **Important:** During Python installation, check the box that says **"Add Python to PATH"**

## Getting Started (3 Easy Steps)

### Step 1: Download NatLangChain

**Option A: Download ZIP**
1. Go to https://github.com/kase1111-hash/NatLangChain
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Extract the ZIP to a folder (e.g., `C:\NatLangChain`)

**Option B: Using Git**
```
git clone https://github.com/kase1111-hash/NatLangChain.git
```

### Step 2: Run the Build Script

1. Open the NatLangChain folder
2. **Double-click `build.bat`**

That's it! The script will automatically:
- ✅ Create a virtual environment
- ✅ Install all dependencies
- ✅ Set up configuration
- ✅ Start the server

### Step 3: Start Using NatLangChain

Once you see this message:
```
Server starting at http://localhost:5000
```

Open your web browser and go to: **http://localhost:5000/health**

You should see: `{"status": "healthy"}`

🎉 **Congratulations! NatLangChain is running!**

---

## Quick Test

Let's add your first entry to the blockchain!

### Using Your Browser

Visit: http://localhost:5000/chain

You'll see the blockchain with the genesis block.

### Using Command Line (Optional)

Open a new Command Prompt and run:

```cmd
curl -X POST http://localhost:5000/entry -H "Content-Type: application/json" -d "{\"content\": \"My first entry!\", \"author\": \"me\", \"intent\": \"Testing\"}"
```

---

## Common Questions

### How do I stop the server?

Press `Ctrl + C` in the command window.

### How do I start it again?

Double-click `build.bat` again. It will skip setup and start the server directly.

### I see "ANTHROPIC_API_KEY" warnings?

That's okay for basic use! The API key is only needed for advanced AI features like:
- Smart contract matching
- Semantic search
- LLM-powered validation

To enable these features:
1. Get a free API key from https://console.anthropic.com/
2. Open the `.env` file in the NatLangChain folder
3. Add your key: `ANTHROPIC_API_KEY=your_key_here`
4. Restart the server

### The script says "Python is not installed"?

1. Download Python from https://www.python.org/downloads/
2. **Important:** Check "Add Python to PATH" during installation
3. Restart your computer
4. Try running `build.bat` again

### Can I build the desktop app?

Yes! But you'll need additional tools:
- Node.js (https://nodejs.org)
- Rust (https://rustup.rs)
- Visual Studio Build Tools

Then run `build-full.bat` instead.

---

## What's Next?

Now that NatLangChain is running, you can:

1. **Read the User Manual** - `docs/user-manual.md`
2. **Explore the API** - See `API.md` for all available endpoints
3. **Learn the concepts** - Check `SPEC.md` for how everything works

---

## File Reference

| File | What it does |
|------|--------------|
| `build.bat` | Sets up and runs the API server |
| `build-full.bat` | Builds everything including the desktop app |
| `.env` | Your configuration settings |
| `src/api.py` | The main server code |

---

## Need Help?

- Check the [FAQ](FAQ.md)
- Read the [full documentation](docs/README.md)
- Open an issue on GitHub

---

**Happy building!** 🚀
