// Paste this in the browser console when on ELK (localhost:3004)

console.clear();
console.log("🔍 Checking ELK-Corgi connection...\n");

// Check localStorage for Corgi configuration
const checkStorage = () => {
  console.log("📦 Checking localStorage:");
  const corgiKeys = Object.keys(localStorage).filter(k => 
    k.toLowerCase().includes('corgi') || 
    k.includes('api') ||
    k.includes('recommendation')
  );
  
  if (corgiKeys.length > 0) {
    console.log("Found potential Corgi-related keys:");
    corgiKeys.forEach(key => {
      console.log(`  ${key}: ${localStorage.getItem(key)}`);
    });
  } else {
    console.log("  No Corgi-related keys found");
  }
};

// Check window object for API configuration
const checkWindowConfig = () => {
  console.log("\n🪟 Checking window configuration:");
  if (window.__CORGI_API_BASE_URL) {
    console.log(`  Corgi API URL: ${window.__CORGI_API_BASE_URL}`);
  } else {
    console.log("  No Corgi API URL configured in window");
  }
};

// Check recent network requests
const checkNetworkCalls = () => {
  console.log("\n🌐 Checking recent network calls:");
  const entries = performance.getEntriesByType('resource');
  const corgiCalls = entries.filter(e => 
    e.name.includes(':9999') || 
    e.name.includes(':5002') ||
    e.name.includes('corgi') ||
    e.name.includes('recommendation')
  );
  
  if (corgiCalls.length > 0) {
    console.log("Found Corgi-related calls:");
    corgiCalls.forEach(call => {
      console.log(`  ${call.name}`);
    });
  } else {
    console.log("  ❌ No calls to Corgi API detected");
    console.log("  ELK might not be configured to use Corgi!");
  }
};

// Test Corgi API connectivity
const testCorgiAPI = async () => {
  console.log("\n🧪 Testing Corgi API endpoints:");
  
  // Test port 9999 (where Corgi actually is)
  try {
    const resp = await fetch('http://localhost:9999/health');
    if (resp.ok) {
      console.log("  ✅ Corgi API responding on port 9999");
    }
  } catch (e) {
    console.log("  ❌ Cannot reach Corgi on port 9999");
  }
  
  // Test port 5002 (where ELK expects it)
  try {
    const resp = await fetch('http://localhost:5002/health');
    if (resp.ok) {
      console.log("  ✅ Something responding on port 5002");
    } else {
      console.log("  ❌ Port 5002 not responding (ELK's expected port)");
    }
  } catch (e) {
    console.log("  ❌ Nothing on port 5002 (ELK's expected port)");
  }
};

// Run all checks
checkStorage();
checkWindowConfig();
checkNetworkCalls();
await testCorgiAPI();

console.log("\n💡 DIAGNOSIS:");
console.log("If ELK is not connecting to Corgi, you need to:");
console.log("1. Configure ELK to use port 9999 instead of 5002");
console.log("2. OR start Corgi on port 5002");
console.log("3. OR use a proxy to forward 5002 → 9999");

console.log("\n🔧 Quick fix - run this to set Corgi URL:");
console.log("window.__CORGI_API_BASE_URL = 'http://localhost:9999';");
console.log("localStorage.setItem('corgi_api_url', 'http://localhost:9999');"); 