const path = require('path')

module.exports = {
  entry: './js/lights.js',
  output: {
    path: path.resolve(__dirname, 'html/js'),
    filename: 'lights-bundle.js'
  },
};