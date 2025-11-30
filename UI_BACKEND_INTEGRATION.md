# UI-Backend Integration Implementation

This document describes the implementation of UI controls connected to backend orchestration settings.

## Overview

All UI controls have been successfully connected to the backend orchestration system. The implementation includes:

1. **Accuracy-Speed Slider**: Maps to backend `mode` parameter
2. **Domain Presets Dropdown**: Configures model selection and security rules
3. **Feature Toggles**: Controls DeepConf and verification features
4. **Live Status Updates**: Polling-based status endpoint for real-time updates

## Implementation Details

### 1. Accuracy-Speed Slider

**Frontend**: `ui/components/criteria-equalizer.tsx`
- Users can adjust accuracy, speed, and creativity sliders
- Settings are stored in `criteriaSettings` state

**Backend Mapping**: `llmhive/src/llmhive/app/api/orchestration.py`
- `criteriaSettings` is sent from frontend to backend
- Backend derives `mode` from `criteriaSettings`:
  - If `speed > accuracy + 20`: mode = "speed"
  - Otherwise: mode = "accuracy"
- Mode is passed to orchestrator for adaptive model selection

**Behavior**:
- **Speed Mode**: Limits to 1-2 models, skips DeepConf and verification
- **Accuracy Mode**: Uses 3-4 models, enables full consensus and verification

### 2. Domain Presets Dropdown

**Frontend**: `ui/components/chat-header.tsx`
- New dropdown with options: General, Medical, Legal, Research
- Selected preset is stored in `preset` state

**Backend Handling**: `llmhive/src/llmhive/app/orchestrator.py`
- `preset` parameter is accepted in `orchestrate()` method
- Preset-specific configurations:
  - **Medical**: Enables strict guardrails, prefers medical-focused models
  - **Legal**: Enables fact-checking by default, prefers legal reasoning models
  - **Research**: Enables deep verification, prefers research-capable models
  - **General**: Uses default settings

**Schema**: `llmhive/src/llmhive/app/schemas.py`
- Added `preset: Optional[str]` to `OrchestrationRequest`

### 3. Feature Toggles

**Frontend**: `ui/components/chat-header.tsx`
- New toggles in Advanced dropdown:
  - "Enable Challenge Loop (DeepConf)"
  - "Enable Deep Verification"
- Toggles are stored in `useDeepconf` and `useVerification` state

**Backend Handling**: `llmhive/src/llmhive/app/orchestrator.py`
- `use_deepconf` and `use_verification` parameters accepted
- Feature toggles override default behavior:
  - If `use_deepconf=False`: Skips DeepConf challenge loop even if protocol is "deep-conf"
  - If `use_verification=False`: Skips fact-checking even in accuracy mode
- Subscription tier enforcement: Free tier users cannot enable restricted features

**Schema**: `llmhive/src/llmhive/app/schemas.py`
- Added `use_deepconf: Optional[bool]` to `OrchestrationRequest`
- Added `use_verification: Optional[bool]` to `OrchestrationRequest`

### 4. Live Status Updates

**Backend**: `llmhive/src/llmhive/app/api/status.py`
- New status endpoint: `GET /api/v1/status/{query_id}`
- Returns current processing stage, status, model, progress, and message
- Status can be updated via `POST /api/v1/status/{query_id}`
- Status can be cleared via `DELETE /api/v1/status/{query_id}`

**Status Fields**:
- `stage`: Current processing stage (e.g., "planning", "model_query", "verification")
- `status`: Status of current stage ("running", "completed", "error")
- `model`: Current model being used (if applicable)
- `progress`: Progress percentage (0-100)
- `message`: Human-readable status message
- `timestamp`: Last update timestamp

**Frontend Integration** (Future):
- Frontend can poll `/api/v1/status/{query_id}` to get real-time updates
- Query ID should be generated on the frontend and passed to backend
- Backend should update status at key orchestration stages

## API Changes

### New Request Parameters

The `OrchestrationRequest` schema now includes:

```python
preset: Optional[str]  # Domain preset: "medical", "legal", "research", "general"
use_deepconf: Optional[bool]  # Enable/disable DeepConf challenge loop
use_verification: Optional[bool]  # Enable/disable fact-checking
criteria_settings: Optional[Dict[str, Any]]  # Frontend criteria settings
```

### New Endpoints

- `GET /api/v1/status/{query_id}`: Get query status
- `POST /api/v1/status/{query_id}`: Update query status (internal)
- `DELETE /api/v1/status/{query_id}`: Clear query status

## Testing

### Manual Testing Steps

1. **Accuracy-Speed Slider**:
   - Open UI and adjust criteria sliders
   - Set speed to 100 and accuracy to 50
   - Submit a query and check backend logs for "mode='speed'"
   - Verify fewer models are used and verification is skipped

2. **Domain Presets**:
   - Select "Medical" preset from dropdown
   - Submit a query and check backend logs for "Medical preset"
   - Verify strict guardrails are enabled

3. **Feature Toggles**:
   - Enable "Enable Challenge Loop (DeepConf)" toggle
   - Submit a query with protocol "deep-conf"
   - Verify DeepConf challenge loop executes
   - Disable toggle and verify DeepConf is skipped

4. **Status Updates**:
   - Generate a query ID on frontend
   - Poll `/api/v1/status/{query_id}` during query processing
   - Verify status updates reflect current orchestration stage

## Subscription Tier Enforcement

Feature toggles respect subscription tiers:
- **Free Tier**: Cannot enable DeepConf or advanced features
- **Pro Tier**: Can enable all features
- **Enterprise Tier**: Full access to all features

If a user tries to enable a restricted feature, the backend will:
1. Log a warning
2. Disable the feature automatically
3. Continue processing with allowed features

## Files Modified

### Backend
- `llmhive/src/llmhive/app/schemas.py`: Added new request parameters
- `llmhive/src/llmhive/app/api/orchestration.py`: Added parameter mapping and tier enforcement
- `llmhive/src/llmhive/app/orchestrator.py`: Added preset handling and feature toggle logic
- `llmhive/src/llmhive/app/api/status.py`: New status endpoint
- `llmhive/src/llmhive/app/api/__init__.py`: Added status router

### Frontend
- `ui/app/api/chat/route.ts`: Added parameter forwarding
- `ui/components/chat-area.tsx`: Added state for new parameters
- `ui/components/chat-header.tsx`: Added preset dropdown and feature toggles

## Next Steps (Optional Enhancements)

1. **WebSocket Implementation**: Replace polling with WebSocket for real-time status updates
2. **Status Integration**: Integrate status updates into orchestrator workflow
3. **UI Status Display**: Add visual status indicators in frontend
4. **Preset Customization**: Allow users to create custom domain presets
5. **Feature Tooltips**: Add tooltips explaining each feature toggle

## Notes

- All changes maintain backward compatibility
- Default behavior is preserved when parameters are not provided
- Subscription tier enforcement is transparent to users (features are disabled automatically)
- Status endpoint uses in-memory storage (consider Redis for production)

