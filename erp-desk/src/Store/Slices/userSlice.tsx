// src/store/slices/userSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { getUserDetails } from '../../Utils/helpers';

export const fetchUserData = createAsyncThunk('user/fetchUserData', async () => {
  const res = await getUserDetails();
  return res;
});

const userSlice = createSlice({
  name: 'user',
  initialState: {
    data: null,
    loading: false,
    error: null,
  },
  reducers: {
    clearUserData: (state: any) => {
      state.data = null;
    },
  },
  extraReducers: (builder: any) => {
    builder
      .addCase(fetchUserData.pending, (state: any) => {
        state.loading = true;
      })
      .addCase(fetchUserData.fulfilled, (state: any, action: any) => {
        state.data = action.payload;
        state.loading = false;
      })
      .addCase(fetchUserData.rejected, (state: any, action: any) => {
        state.error = action.error;
        state.loading = false;
      });
  },
});

export const { clearUserData } = userSlice.actions;
export default userSlice.reducer;
