import Chart from 'kaktana-react-lightweight-charts'
const Box = ({ areaSeries, options, coinData }) => {
  return (
    <div id='chart'>
      <div className='three-line-legend'>
        <span style={{ fontSize: '32px' }}>
            { coinData.name }
        </span>
        <span style={{ fontSize: '16px', fontWeight: '100', fontStyle: 'italic' }}>
            <br />
            Pirce: { `$${coinData.price}` }
            <br />
            Volume: { coinData.volume }
            <br />
            Market Cap: { coinData.marketCap }
        </span>
      </div>
      <Chart
        options={ options }
        areaSeries={ [{
          data: areaSeries,
          options: {
            topColor: 'rgba(19, 68, 193, 0.4)',
            bottomColor: 'rgba(0, 120, 255, 0.0)',
            lineColor: 'rgba(19, 40, 153, 1.0)',
            lineWidth: 3,
          }
        }]}
        autoWidth={ true }
        height={320}
        from={ areaSeries[0]['time'] }
        to={ areaSeries[areaSeries.length - 1]['time'] }
      />
    </div>
  )
}

export default Box
