/* ── Root App component ── */
(function () {
  const { useState, useEffect, useCallback, useRef } = React;

  function App() {
    const [page,            setPage]            = useState('predict');
    const [stations,        setStations]        = useState([]);
    const [selected,        setSelected]        = useState('');
    const [pipeStatus,      setPipeStatus]      = useState(null);
    const [result,          setResult]          = useState(null);
    const [history,         setHistory]         = useState([]);
    const [mockMode,        setMockMode]        = useState(false);
    const [toast,           setToast]           = useState(null);
    /* highlightFeature: feature key to scroll-to in FeaturesPage */
    const [highlightFeature, setHighlightFeature] = useState(null);
    const toastTimer = useRef(null);

    /* Toast helper */
    const showToast = useCallback((message, type = 'info') => {
      clearTimeout(toastTimer.current);
      setToast({ message, type });
      toastTimer.current = setTimeout(() => setToast(null), 4000);
    }, []);

    /* Fetch functions */
    const fetchStations = useCallback(async () => {
      try {
        const d = await MS.api.get('/stations');
        setStations(d);
        setSelected(s => s || (d[0]?.station_id ?? ''));
      } catch {
        showToast('Backend chưa khởi động — chạy run.sh trước', 'error');
      }
    }, []);

    const fetchPipe = useCallback(async () => {
      try { setPipeStatus(await MS.api.get('/pipeline/status')); } catch {}
    }, []);

    const fetchHistory = useCallback(async () => {
      try { setHistory(await MS.api.get('/history')); } catch {}
    }, []);

    /* Result callback from PredictionPanel */
    const handleResult = useCallback((r, stationId) => {
      setResult(r);
      if (r) {
        setMockMode(r.mock);
        if (stationId) setSelected(stationId);
        fetchHistory();
      }
    }, []);

    const handleDeleteHistory = async (id) => {
      try { await MS.api.del(`/history/${id}`); fetchHistory(); } catch {}
    };
    const handleClearHistory = async () => {
      try { await MS.api.del('/history/all'); fetchHistory(); } catch {}
    };

    const triggerPipeline = useCallback(async () => {
      try {
        await MS.api.post('/pipeline/run', {});
        showToast('Pipeline đã được kích hoạt thành công', 'success');
        setTimeout(fetchPipe, 3000);
      } catch (e) {
        showToast(`Lỗi kích hoạt pipeline: ${e.message}`, 'error');
      }
    }, []);

    /* ── Navigate to feature detail from prediction panel ── */
    /* Called by prediction.js when user clicks a feature label */
    MS.navigateToFeature = useCallback((featureKey) => {
      setHighlightFeature(featureKey);
      setPage('features');
    }, []);

    /* Init */
    useEffect(() => {
      fetchStations();
      fetchPipe();
      fetchHistory();
      const interval = setInterval(fetchPipe, 30000);
      return () => clearInterval(interval);
    }, []);

    function renderPage() {
      if (page === 'features') {
        return (
          <MS.FeaturesPage
            highlightFeature={highlightFeature}
            onClearHighlight={() => setHighlightFeature(null)}
          />
        );
      }
      if (page === 'map') {
        return (
          <MS.MapPage
            stations={stations}
            selected={selected}
            onSelect={(sid) => setSelected(sid)}
          />
        );
      }
      if (page === 'about') {
        return <MS.AboutPage />;
      }
      /* default: predict */
      return (
        <>
          {mockMode && (
            <div className="mock-banner">
              <i className="ti ti-alert-triangle" style={{ fontSize:'16px', flexShrink:0 }} />
              <span>
                <strong>Demo Mode</strong> — Model file chưa được load. Kết quả mô phỏng từ công thức salinity + NDVI.
                Chạy <code>python setup_model.py --data_path &lt;path&gt;</code> để load model thật.
              </span>
            </div>
          )}
          <div className="layout">
            <MS.MapPanel
              stations={stations}
              selected={selected}
              onSelect={(sid) => setSelected(sid)}
            />
            {/* selectedStation keeps PredictionPanel in sync with map/list clicks */}
            <MS.PredictionPanel
              stations={stations}
              selectedStation={selected}
              onSelectStation={(sid) => setSelected(sid)}
              onResult={handleResult}
              onShowToast={showToast}
            />
            <MS.AnalysisPanel
              result={result}
              history={history}
              onDeleteHistory={handleDeleteHistory}
              onClearHistory={handleClearHistory}
            />
          </div>
        </>
      );
    }

    return (
      <div>
        <MS.Header
          pipeStatus={pipeStatus}
          onTriggerPipeline={triggerPipeline}
          page={page}
          onSetPage={(p) => {
            setPage(p);
            /* Clear highlight when navigating away from features manually */
            if (p !== 'features') setHighlightFeature(null);
          }}
        />
        {renderPage()}
        <MS.Toast toast={toast} />
      </div>
    );
  }

  /* Mount */
  ReactDOM.createRoot(document.getElementById('root')).render(<App />);
}());