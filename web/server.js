const express = require('express');
const app = express();

const WEB_SERVER_PORT = process.env.WEB_SERVER_PORT || 3000;
const SLICE_API_URL = process.env.SLICE_API_URL || 'http://localhost:8000/slice/';
const port = WEB_SERVER_PORT;

var fs = require('fs');
app.engine('ntl', function (filePath, options, callback) {
    fs.readFile(filePath, function (err, content) {
        if (err) return callback(err)
        var rendered = content.toString()
            .replace('#SLICE_API_URL#', options.sliceApiUrl);
        return callback(null, rendered)
    })
});
app.set('views', './views');
app.set('view engine', 'ntl');

app.get('/', function (req, res) {
    res.render('index', {sliceApiUrl: SLICE_API_URL})
});

app.get('/iframe', function (req, res) {
    res.render('iframe', {sliceApiUrl: SLICE_API_URL})
});
app.use('/node_modules', express.static('node_modules'));

app.listen(port, () => console.log(`BeatSlice.it web server listening on port ${port}!`));