const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');

const app = express();
app.use(bodyParser.json());
app.use(express.static('public'));

// Vulnerable recursive merge function
const merge = (target, source) => {
    for (let key in source) {
        if (typeof target[key] === 'object' && typeof source[key] === 'object') {
            merge(target[key], source[key]);
        } else {
            target[key] = source[key];
        }
    }
    return target;
};

// Database simulation
const users = [
    { username: "admin", isAdmin: true },
    { username: "guest", isAdmin: false }
];

app.post('/api/update-settings', (req, res) => {
    let userSettings = {};
    // VULNERABILITY: Unsafe merge of user input into an object
    // This allows polluting Object.prototype if __proto__ is passed
    merge(userSettings, req.body);
    
    // Check if the pollution was successful
    // In a real attack, this would affect other checks in the application
    let response = { status: "Settings updated" };
    
    // Demonstration check:
    if (({}).isAdmin) {
        response.polluted = true;
        response.message = "WARNING: Object.prototype has been polluted! isAdmin is now true for all objects.";
    }
    
    res.json(response);
});

// Admin check endpoint
app.get('/api/admin-check', (req, res) => {
    // A generic object that shouldn't have isAdmin unless polluted
    const checkObj = {};
    
    if (checkObj.isAdmin) {
        res.json({ message: "Access GRANTED to Admin Panel (via Prototype Pollution)", flag: "flag{proto_pollution_master}" });
    } else {
        res.json({ message: "Access Denied", isAdmin: false });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

