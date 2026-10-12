/*
 * WebSploit Labs - cybersecurity training environment.
 * Copyright (C) 2019-2026 Omar Santos <https://websploit.org>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * Additional terms under GNU GPL version 3 section 7 are in the COPYRIGHT
 * file at the root of this repository.
 */

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

const PORT = process.env.PORT || 5004;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

