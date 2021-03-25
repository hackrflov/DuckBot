import { useState, useEffect } from 'react'
import './App.css';
import Box from './components/Box'

const App = () => {
  const [options, setOptions] = useState({
    alignLabels: true,
    grid: {
        horzLines: {
			color: '#eee',
            visible: false,
		},
		vertLines: {
			color: '#ffffff',
		},
	},
    crosshair: {
  		horzLine: {
            visible: false,
            labelVisible: false
        },
        vertLine: {
            visible: true,
            style: 0,
            width: 2,
            color: 'rgba(32, 38, 46, 0.1)',
            labelVisible: false,
        },
    },
    watermark: {
      color: 'rgba(11, 94, 29, 0.4)',
      visible: true,
      text: 'Powered by Tradingview',
      fontSize: 15,
      horzAlign: 'center',
      vertAlign: 'top',
    },
    layout: {
      textColor: '#696969',
      fontSize: 12,
      fontFamily: 'Calibri',
    },
  })
  const [areaSeries, setAreaSeries] = useState({})
  const [coinData, setCoinData] = useState({})

  useEffect(() => {
    const fetchData = async () => {
      console.log('start fetch')
      //const data = await fetch('http://localhost:5000/chart-data')
      const res = await fetch('http://47.117.41.47:5000/chart-data')
      var data = await res.json()
      data = data[0]
      console.log('get response')
      console.log(data)
      const newData = data['prices'].map((v) => {
        return {
          time: v['time'],
          value: v['value'],
        }
      })
      console.log('change data')
      setAreaSeries(newData)
      const num = data['prices'].length - 1
      setCoinData({
        name: data['name'],
        price: Math.round(data['prices'][num]['value'] * 100) / 100,
        volume: data['volumes'][num],
        marketCap: data['marketCaps'][num],
      })
      console.log(areaSeries)
    }

    console.log('in use effect')
    fetchData()
  }, [])

  return (
    <div className="container">
      {areaSeries.length > 0 ? (
        <Box
          areaSeries={ areaSeries }
          coinData={ coinData }
          options={ options }
        />
      ) : (
      'Wait'
      )}
    </div>
  );
}

export default App
