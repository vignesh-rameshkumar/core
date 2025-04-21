import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { getModules, getUserDetails } from '../../Utils/helpers';

export interface UserState {
  userData: any;
  modules: any[];
  loading: boolean;
  error: any;
}

export const fetchUserData : any = createAsyncThunk('user/fetchUserData', async () => {
  const res = await getUserDetails();
  return res;
});


export const fetchUserModules : any = createAsyncThunk('user/fetchUserModules', async () => {
  const res = await getModules();
  return res || [];
});

const initialState: UserState = {
  userData: null,
  modules: [],
  loading: false,
  error: null,
};

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    clearUserData: (state: any) => {
      state.userData = null;
      state.roles = [];
      state.modules = [];
    },
  },
  extraReducers: (builder: any) => {
    builder
      .addCase(fetchUserData.pending, (state: any) => {
        state.loading = true;
      })
      .addCase(fetchUserData.fulfilled, (state: any, action: PayloadAction<any>) => {
        state.userData = action.payload;
        state.loading = false;
      })
      .addCase(fetchUserData.rejected, (state: any, action: any) => {
        state.error = action.error;
        state.loading = false;
      })

      .addCase(fetchUserModules.pending, (state: any) => {
        state.loading = true;
      })
      .addCase(fetchUserModules.fulfilled, (state: any, action: PayloadAction<any[]>) => {
        state.modules = action.payload;
        state.loading = false;
      })
      .addCase(fetchUserModules.rejected, (state: any, action: any) => {
        state.error = action.error;
        state.loading = false;
      });
  },
});

export const { clearUserData } = userSlice.actions;
export default userSlice.reducer;
