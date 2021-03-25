import { useState } from 'react'
import Chart from 'kaktana-react-lightweight-charts'
import './App.css';

const App = () => {
  const [options, setOptions] = useState({
    alignLabels: true,
    grid: {
      vertLines: {
          color: 'rgba(70, 130, 180, 0.5)',
          style: 1,
          visible: true,
      },
      horzLines: {
          color: 'rgba(70, 130, 180, 0.5)',
          style: 1,
          visible: true,
      },
    },
    watermark: {
      color: 'rgba(11, 94, 29, 0.4)',
      visible: true,
      text: 'Powered by TradingView',
      fontSize: 18,
      horzAlign: 'left',
      vertAlign: 'bottom',
    },
    layout: {
      textColor: '#696969',
      fontSize: 12,
      fontFamily: 'Calibri',
    },
  })
  const [candlestickSeries, setCandlestickSeries] = useState([{
    data: [
      { time: '2018-10-19', open: 180.34, high: 180.99, low: 178.57, close: 179.85 },
      { time: '2018-10-22', open: 180.82, high: 181.40, low: 177.56, close: 178.75 },
      { time: '2018-10-23', open: 175.77, high: 179.49, low: 175.44, close: 178.53 },
      { time: '2018-10-24', open: 178.58, high: 182.37, low: 176.31, close: 176.97 },
      { time: '2018-10-25', open: 177.52, high: 180.50, low: 176.83, close: 179.07 },
      { time: '2018-10-26', open: 176.88, high: 177.34, low: 170.91, close: 172.23 },
      { time: '2018-10-29', open: 173.74, high: 175.99, low: 170.95, close: 173.20 },
      { time: '2018-10-30', open: 173.16, high: 176.43, low: 172.64, close: 176.24 },
      { time: '2018-10-31', open: 177.98, high: 178.85, low: 175.59, close: 175.88 },
      { time: '2018-11-01', open: 176.84, high: 180.86, low: 175.90, close: 180.46 },
      { time: '2018-11-02', open: 182.47, high: 183.01, low: 177.39, close: 179.93 },
      { time: '2018-11-05', open: 181.02, high: 182.41, low: 179.30, close: 182.19 }
    ]
  }])

  return (
    <div className="container">
      <Chart
        options={ options }
        candlestickSeries={ candlestickSeries }
        autoWidth={ true }
        legend={ 'KDA price' }
        height={320}
        from={ '2018-10-01' }
        to={ '2018-12-01' }
      />
    </div>
  );
}

export default App
