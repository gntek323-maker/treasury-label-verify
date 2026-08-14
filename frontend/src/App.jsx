import React, { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

// Status badge colors
const statusColors = {
  APPROVED: 'bg-green-100 text-green-800 border-green-300',
  NEEDS_REVIEW: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  MISMATCH_DETECTED: 'bg-red-100 text-red-800 border-red-300',
}

const statusIcons = {
  APPROVED: '✓',
  NEEDS_REVIEW: '⚠',
  MISMATCH_DETECTED: '✗',
}

function App() {
  const [mode, setMode] = useState('single') // 'single' or 'batch'
  const [image, setImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [formData, setFormData] = useState({
    brand_name: '',
    class_type: '',
    alcohol_content: '',
    net_contents: '',
    producer_name: '',
    government_warning: '',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Batch mode state
  const [batchFiles, setBatchFiles] = useState([])
  const [batchResults, setBatchResults] = useState(null)

  const handleImageChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      setImage(file)
      setImagePreview(URL.createObjectURL(file))
      setResult(null)
      setError(null)
    }
  }

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!image) {
      setError('Please upload a label image.')
      return
    }
    if (!formData.brand_name.trim()) {
      setError('Brand name is required.')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    const data = new FormData()
    data.append('image', image)
    data.append('brand_name', formData.brand_name)
    data.append('class_type', formData.class_type)
    data.append('alcohol_content', formData.alcohol_content)
    data.append('net_contents', formData.net_contents)
    data.append('producer_name', formData.producer_name)
    data.append('government_warning', formData.government_warning)

    try {
      const response = await fetch(`${API_URL}/verify`, {
        method: 'POST',
        body: data,
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Verification failed')
      }

      const resultData = await response.json()
      setResult(resultData)
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setImage(null)
    setImagePreview(null)
    setFormData({
      brand_name: '',
      class_type: '',
      alcohol_content: '',
      net_contents: '',
      producer_name: '',
      government_warning: '',
    })
    setResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-blue-900 text-white py-4 px-6 shadow-md">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">TTB Label Verification Tool</h1>
            <p className="text-blue-200 text-sm">AI-Powered Alcohol Label Compliance Check</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setMode('single')}
              className={`px-4 py-2 rounded text-sm font-medium ${
                mode === 'single'
                  ? 'bg-white text-blue-900'
                  : 'bg-blue-800 text-blue-100 hover:bg-blue-700'
              }`}
            >
              Single Label
            </button>
            <button
              onClick={() => setMode('batch')}
              className={`px-4 py-2 rounded text-sm font-medium ${
                mode === 'batch'
                  ? 'bg-white text-blue-900'
                  : 'bg-blue-800 text-blue-100 hover:bg-blue-700'
              }`}
            >
              Batch Upload
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto py-8 px-6">
        {mode === 'single' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left side: Upload and Form */}
            <div className="space-y-6">
              {/* Image Upload */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4 text-gray-800">
                  Step 1: Upload Label Image
                </h2>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
                  {imagePreview ? (
                    <div>
                      <img
                        src={imagePreview}
                        alt="Label preview"
                        className="max-h-48 mx-auto rounded mb-4"
                      />
                      <button
                        onClick={() => { setImage(null); setImagePreview(null) }}
                        className="text-sm text-red-600 hover:text-red-800"
                      >
                        Remove image
                      </button>
                    </div>
                  ) : (
                    <label className="cursor-pointer block">
                      <div className="text-4xl mb-2">📷</div>
                      <p className="text-gray-600 mb-2">
                        Click to upload or drag and drop
                      </p>
                      <p className="text-gray-400 text-sm">
                        JPEG, PNG, or WebP (max 20MB)
                      </p>
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        onChange={handleImageChange}
                        className="hidden"
                      />
                    </label>
                  )}
                </div>
              </div>

              {/* Application Data Form */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4 text-gray-800">
                  Step 2: Enter Application Data
                </h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Brand Name *
                    </label>
                    <input
                      type="text"
                      name="brand_name"
                      value={formData.brand_name}
                      onChange={handleInputChange}
                      placeholder="e.g., OLD TOM DISTILLERY"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Class/Type
                    </label>
                    <input
                      type="text"
                      name="class_type"
                      value={formData.class_type}
                      onChange={handleInputChange}
                      placeholder="e.g., Kentucky Straight Bourbon Whiskey"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Alcohol Content
                      </label>
                      <input
                        type="text"
                        name="alcohol_content"
                        value={formData.alcohol_content}
                        onChange={handleInputChange}
                        placeholder="e.g., 45%"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Net Contents
                      </label>
                      <input
                        type="text"
                        name="net_contents"
                        value={formData.net_contents}
                        onChange={handleInputChange}
                        placeholder="e.g., 750 mL"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Producer/Bottler
                    </label>
                    <input
                      type="text"
                      name="producer_name"
                      value={formData.producer_name}
                      onChange={handleInputChange}
                      placeholder="e.g., Old Tom Distillery, Louisville, KY"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Government Warning Statement
                    </label>
                    <textarea
                      name="government_warning"
                      value={formData.government_warning}
                      onChange={handleInputChange}
                      placeholder="GOVERNMENT WARNING: (1) According to the Surgeon General..."
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-3 pt-2">
                    <button
                      type="submit"
                      disabled={loading}
                      className="flex-1 bg-blue-700 text-white py-3 px-6 rounded-md font-medium text-lg hover:bg-blue-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                      {loading ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="animate-spin">⟳</span> Verifying...
                        </span>
                      ) : (
                        'Verify Label'
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleReset}
                      className="px-6 py-3 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      Clear
                    </button>
                  </div>
                </form>
              </div>
            </div>

            {/* Right side: Results */}
            <div>
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                  <p className="text-red-800 font-medium">Error</p>
                  <p className="text-red-600">{error}</p>
                </div>
              )}

              {result && (
                <div className="bg-white rounded-lg shadow p-6 space-y-6">
                  {/* Overall Status */}
                  <div className={`border rounded-lg p-4 ${statusColors[result.overall_status]}`}>
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{statusIcons[result.overall_status]}</span>
                      <div>
                        <h3 className="text-xl font-bold">{result.overall_status.replace('_', ' ')}</h3>
                        <p className="text-sm">
                          Confidence: {Math.round(result.overall_confidence * 100)}% | 
                          Processed in {result.processing_time_seconds}s
                        </p>
                      </div>
                    </div>
                    {result.needs_human_review && (
                      <div className="mt-3 pt-3 border-t border-current border-opacity-20">
                        <p className="font-medium text-sm">⚠ Human Review Recommended:</p>
                        <ul className="list-disc list-inside text-sm mt-1">
                          {result.review_reasons.map((reason, i) => (
                            <li key={i}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Field-by-Field Results */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3 text-gray-800">
                      Field-by-Field Comparison
                    </h3>
                    <div className="space-y-3">
                      {result.fields.map((field, i) => (
                        <div
                          key={i}
                          className={`border rounded-lg p-4 ${
                            field.match
                              ? 'border-green-200 bg-green-50'
                              : 'border-red-200 bg-red-50'
                          }`}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <p className="font-medium text-gray-800">
                                {field.match ? '✓' : '✗'} {field.field_name}
                              </p>
                              <div className="mt-1 text-sm space-y-1">
                                <p>
                                  <span className="text-gray-500">Application:</span>{' '}
                                  {field.application_value}
                                </p>
                                <p>
                                  <span className="text-gray-500">Label:</span>{' '}
                                  {field.extracted_value}
                                </p>
                              </div>
                              {field.notes && (
                                <p className="text-xs text-gray-500 mt-1 italic">{field.notes}</p>
                              )}
                            </div>
                            <div className="text-right">
                              <span
                                className={`text-sm font-medium px-2 py-1 rounded ${
                                  field.confidence >= 0.9
                                    ? 'bg-green-200 text-green-800'
                                    : field.confidence >= 0.7
                                    ? 'bg-yellow-200 text-yellow-800'
                                    : 'bg-red-200 text-red-800'
                                }`}
                              >
                                {Math.round(field.confidence * 100)}%
                              </span>
                              <p className="text-xs text-gray-400 mt-1">{field.match_type}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {!result && !error && (
                <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400">
                  <div className="text-5xl mb-4">🏷️</div>
                  <p className="text-lg">Upload a label and enter application data to start verification</p>
                  <p className="text-sm mt-2">Results will appear here</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Batch Mode */
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">
              Batch Upload (Coming Soon)
            </h2>
            <p className="text-gray-600 mb-4">
              Upload multiple label images with a CSV of application data for bulk processing.
              Designed for importers submitting 200-300 applications at once.
            </p>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
              <div className="text-4xl mb-3">📁</div>
              <p className="text-gray-500">
                Drag and drop multiple label images here, or click to select files
              </p>
              <p className="text-gray-400 text-sm mt-2">
                Supported: JPEG, PNG, WebP | Max 300 files per batch
              </p>
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => setBatchFiles(Array.from(e.target.files))}
                className="hidden"
                id="batch-upload"
              />
              <label
                htmlFor="batch-upload"
                className="inline-block mt-4 px-6 py-3 bg-blue-700 text-white rounded-md cursor-pointer hover:bg-blue-800"
              >
                Select Files
              </label>
              {batchFiles.length > 0 && (
                <p className="mt-3 text-green-600 font-medium">
                  {batchFiles.length} files selected
                </p>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-4 text-gray-400 text-sm">
        <p>AI-Powered Label Verification Prototype | Department of Treasury Assessment</p>
      </footer>
    </div>
  )
}

export default App
