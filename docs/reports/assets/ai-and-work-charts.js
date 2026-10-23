(function () {
  'use strict';
  if (typeof echarts === 'undefined') return;
  var zh = document.documentElement.lang.startsWith('zh');
  var css = getComputedStyle(document.documentElement);
  function token(name) { return css.getPropertyValue(name).trim(); }
  var ink = token('--ink'), muted = token('--muted'), rule = token('--line');
  var paper = token('--paper'), evidence = token('--evidence');
  var projection = token('--proposal') || token('--action');
  var font = token('--body');
  function rows(figure) {
    return Array.from(figure.querySelectorAll('tbody tr')).map(function (row) {
      return { value: Number(row.dataset.value), name: row.querySelector('th').textContent,
        display: row.querySelector('td').textContent };
    });
  }
  function base(color) {
    return { animation: false, color: [color], textStyle: { fontFamily: font, color: ink },
      tooltip: { trigger: 'item', appendToBody: true, backgroundColor: paper, borderColor: rule,
        textStyle: { color: ink, fontFamily: font, fontSize: 14 }, confine: true },
      xAxis: { type: 'value', min: 0, axisLine: { show: true, lineStyle: { color: muted } },
        axisTick: { show: false }, splitLine: { lineStyle: { color: rule } },
        axisLabel: { color: muted, fontSize: 13, margin: 12, hideOverlap: true } },
      yAxis: { type: 'category', inverse: true, axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: ink, fontSize: 14, margin: 16 } } };
  }
  function init(id, makeOption) {
    var el = document.getElementById(id), figure = el.closest('figure'), data = rows(figure);
    var instance;
    try {
      el.hidden = false;
      instance = echarts.init(el, null, { renderer: 'svg' });
      function render() {
        instance.resize();
        instance.setOption(makeOption(data, el.clientWidth < 540), true);
      }
      render();
      figure.classList.add('chart-ready');
      figure.querySelector('details').open = false;
      window.addEventListener('resize', render);
      window.addEventListener('beforeprint', render);
      window.addEventListener('afterprint', render);
      if (document.fonts) document.fonts.ready.then(render);
    } catch (error) {
      if (instance) instance.dispose();
      el.hidden = true;
      figure.querySelector('details').open = true;
      console.error('Chart fallback: ' + id, error);
    }
  }
  init('hiring-chart', function (data, narrow) {
    var option = base(evidence);
    option.grid = { left: narrow ? 105 : 145, right: narrow ? 42 : 75, top: 20, bottom: 40 };
    option.xAxis.max = 30; option.xAxis.interval = 10;
    option.xAxis.axisLabel.formatter = '{value}%';
    option.yAxis.data = data.map(function (d) { return d.name; });
    option.yAxis.axisLabel.formatter = function (label) {
      return narrow && !zh && label === 'End of period' ? 'End of\nperiod' : label;
    };
    option.yAxis.axisLabel.lineHeight = 21;
    option.series = [{ type: 'bar', barWidth: 30, data: data.map(function (d) { return d.value; }),
      itemStyle: { color: evidence }, label: { show: true, position: 'right', distance: 9,
        color: ink, fontSize: 19, fontWeight: 700, formatter: '{c}%' } }];
    option.tooltip.formatter = function (p) { return data[p.dataIndex].name + ': ' + data[p.dataIndex].display; };
    return option;
  });
  init('time-chart', function (data, narrow) {
    var value = data[0].value, low = data[1].value, high = data[2].value;
    var option = base(evidence);
    option.grid = { left: 25, right: narrow ? 30 : 55, top: 36, bottom: 48 };
    option.xAxis.max = 50; option.xAxis.interval = 10;
    option.xAxis.axisLine.onZero = false;
    option.xAxis.axisLabel.formatter = function (v) { return v === 0 ? '0%' : '+' + v + '%'; };
    option.yAxis = { type: 'value', min: -1, max: 1, show: false };
    option.series = [
      { type: 'custom', silent: true, data: [[low, high]], renderItem: function (params, api) {
        var a = api.coord([api.value(0), 0]), b = api.coord([api.value(1), 0]);
        return { type: 'group', children: [
          { type: 'line', shape: { x1:a[0], y1:a[1], x2:b[0], y2:b[1] }, style: { stroke:evidence, lineWidth:3 } },
          { type: 'line', shape: { x1:a[0], y1:a[1]-9, x2:a[0], y2:a[1]+9 }, style: { stroke:evidence, lineWidth:2 } },
          { type: 'line', shape: { x1:b[0], y1:b[1]-9, x2:b[0], y2:b[1]+9 }, style: { stroke:evidence, lineWidth:2 } },
          { type: 'text', style: { x:a[0], y:a[1]+23, text:'+'+low+'%', fill:muted, font:'14px '+font, align:'center' } },
          { type: 'text', style: { x:b[0], y:b[1]+23, text:'+'+high+'%', fill:muted, font:'14px '+font, align:'center' } }
        ] };
      } },
      { type: 'scatter', data: [[value, 0]], symbolSize: 14, itemStyle: { color:evidence, opacity:1 },
        label: { show:true, position:'top', distance:14, formatter:'+'+value+'%', color:ink, fontSize:23, fontWeight:700 } }
    ];
    option.tooltip.formatter = function () {
      return (zh ? '任务耗时：+' : 'Task time: +') + value + '%<br>' +
        (zh ? '置信区间：+' : 'Reported confidence interval: +') + low + '% – +' + high + '%';
    };
    return option;
  });
  init('jobs-chart', function (data, narrow) {
    var option = base(projection);
    option.grid = { left:narrow ? 94 : 130, right:narrow ? 70 : 125, top:20, bottom:40 };
    option.xAxis.max = 200; option.xAxis.interval = 50;
    option.xAxis.axisLabel.formatter = function (v) {
      return zh ? (v === 0 ? '0' : v / 100 + '亿') : (v === 0 ? '0' : v + 'm');
    };
    option.yAxis.data = data.map(function (d) { return d.name; });
    option.series = [{ type:'bar', barWidth:30, data:data.map(function (d, i) {
      return { value:d.value, itemStyle:{ color:i ? muted : projection } };
    }), label:{ show:true, position:'right', distance:9, color:ink, fontSize:narrow ? 16 : 19,
      fontWeight:700, formatter:function (p) { return data[p.dataIndex].display; } } }];
    option.tooltip.formatter = function (p) { return data[p.dataIndex].name + ': ' + data[p.dataIndex].display; };
    return option;
  });
})();
