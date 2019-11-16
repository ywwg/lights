const path = require('path')
var webpack = require('webpack');

module.exports = {
  entry: './js/lights.js',
  output: {
    path: path.resolve(__dirname, 'html/js'),
    filename: 'lights-bundle.js'
  },
  optimization: {
    minimize: false
  }
};
