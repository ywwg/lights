import $ from 'jquery'
import 'popper.js'
import iro from '@jaames/iro'
import 'bootstrap';

// Populates the dropdown list of bulbs.
function load_light_names() {
  $.ajax({
    type: 'GET',
    url: '/list_groups',
    dataType: 'json',
    async: false,
    success: function(lights) {
      for (var i = 0; i < lights.length; i++) {
        $('#lightSelect')
          .append(
            '<option value="' + lights[i] + '">' + lights[i] + '</option>');
      }
    }
  })
  $('#lightSelect').append('<option disabled>──────────</option>');
  $.ajax({
    type: 'GET',
    url: '/list_lights',
    dataType: 'json',
    async: false,
    success: function(lights) {
      for (var i = 0; i < lights.length; i++) {
        $('#lightSelect')
          .append(
            '<option value="' + lights[i] + '">' + lights[i] + '</option>');
      }
    }
  })
}

// Populates the button group of presets.
function load_presets() {
  $.ajax({
    type: 'GET',
    url: '/list_presets',
    dataType: 'json',
    success: function(presets) {
      for (var i = 0; i < presets.length; i++) {
        $('#preset-list')
          .append(
              '<button type="button" class="btn btn-primary" name="button"' +
              'onclick="activate_preset(&quot;' + presets[i] + '&quot;)">' +
              presets[i] + '</button>');
      }
    }
  });
}

// Returns the current light mode, either color or white
function get_mode() {
  return $('#modeSelect input:radio:checked').val();
}

function get_bulb() {
  return $('#lightSelect').val();
}

function get_transition_time() {
  return $('#speedRange').val();
}

function onColorInputStart(color) {
  userInteracting = true;

  // If the selected color has any s, then set mode to color.
  var mode = get_mode();
  var hsl = color.hsl;
  if (mode === 'white' && hsl.s !== 0) {
    $('#mode-color').trigger('click');
  }

  // Due to the ordering of events, color:change happens before input start,
  // so we have to explicitly call onColorChange.
  onColorChange(color);
}

function onColorInputEnd() {
  userInteracting = false;
}

function onColorChange(color, changes) {
  // Ignore changes not triggered by the user.
  if (!userInteracting) {
    return;
  }

  doColorChange(color);
}

function doColorChange(color) {
  var bulb = get_bulb();
  if (bulb === '') {
    console.log('bulb not selected');
    return;
  }

  var mode = get_mode();
  if (mode === 'color') {
    // Trim off '#'
    color = color.hexString.substring(1);
    $.ajax({
      type: 'GET',
      url: '/set_lights?bulb=' + bulb + '&rgbw=' + color + '00',
    });
  } else if (mode === 'white') {
    color = color.hsl.l;
    // Lightness is on a scale from 0-100, not 0x00-0xFF
    var hex = Math.round(((color) / 100.0) * 255).toString(16);
    if (hex.length == 1) {
      hex = "0" + hex;
    }
    $.ajax({
      type: 'GET',
      url: '/set_lights?bulb=' + bulb + '&rgbw=000000' + hex,
    });
  } else {
    console.log('invalid mode:' + mode);
  }
}

function onSpeedChange() {
  $('#speedText').text(get_transition_time());
}

window.activate_preset = function(name) {
  $.ajax({
    type: 'GET',
    url: '/activate_preset?name=' + name
        + '&transition_time=' + get_transition_time(),
    async: false,
  });
  if (progressTimer !== null) {
    clearInterval(progressTimer);
  }
  progressTimer = setInterval(animProgress, PROGRESS_UPDATE_TIME);
}

function animProgress() {
  $.ajax({
    type: 'GET',
    url: '/anim_progress',
    dataType: 'json',
    success: function(progress) {
      if (progress === -1) {
        clearInterval(progressTimer);
        progressTimer = null;
        $('#progressContainer').hide();
        $('#animProgress').attr('aria-valuenow', 0).css('width', '0%');
        return;
      }
      $('#animProgress')
        .attr('aria-valuenow', progress)
        .css('width', progress + '%');
      $('#progressContainer').show();
    }
  });
}

window.set_power = function(onoff) {
  var bulb = get_bulb();
  if (bulb === '') {
    console.log('bulb not selected');
    return;
  }
  $.ajax({
    type: 'GET',
    url: '/set_lights?bulb=' + bulb + '&power=' + onoff,
  });
}

var userInteracting = false;
var progressTimer = null;
const PROGRESS_UPDATE_TIME = 250;

window.init = function() {
  load_light_names();
  load_presets();

  var colorPicker = new iro.ColorPicker('#color-picker-container', {
    wheelLightness: false,
  });
  colorPicker.on('color:change', onColorChange);
  colorPicker.on('input:start', onColorInputStart);
  colorPicker.on('input:end', onColorInputEnd);

  // Reset the color picker to 0% sat when the user selects whites mode so
  // the ui is less confusing.
  $('#modeSelect').on('change', function(ob) {
    console.log('modeselected:' + get_mode());
    if (get_mode() === "white") {
      var curcolor = colorPicker.color;
      var curhsl = curcolor.hsl
      curhsl.s = 0;
      colorPicker.color.hsl = curhsl;
      doColorChange(curcolor);
    } else {
      doColorChange(colorPicker.color);
    }
    return true;
  });

  $('#speedRange').on('input change', onSpeedChange);
  onSpeedChange();
  $('#progressContainer').hide();
}
