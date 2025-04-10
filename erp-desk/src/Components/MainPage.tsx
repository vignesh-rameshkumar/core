import bgImage from '../Assets/background.png';
import ModuleCard from './ModuleCard';
import UserCard from './UserCard';
import EmployeeSearchDrawer from './EmployeeSearchDrawer';
import { filterContainers } from '../Utils/helpers';
import ProductsDrawer from './ProductsDrawer';
import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchUserData, fetchUserModules } from '../Store/Slices/userSlice';
import { RootState } from '../Store';

const MainPage = () => {
    const dispatch = useDispatch();
    const { userData, modules, loading } = useSelector((state: RootState) => state.user);

    useEffect(() => {
        dispatch(fetchUserData());
        dispatch(fetchUserModules());
    }, [dispatch]);
    const filteredContainers = filterContainers(
        modules,
        userData?.roles,
        userData?.department
    );

    return (
        <div className="bg-cover bg-center h-[calc(100vh-17%)] w-full !overflow-hidden"
            style={{ backgroundImage: `url(${bgImage})` }}
        >
            <EmployeeSearchDrawer />
            <ProductsDrawer />
            <div className='grid grid-cols-1 md:grid-cols-3 gap-8 h-full overflow-y-auto py-10 px-5 sm:px-15'>
                <UserCard />
                {filteredContainers?.map((data: any) => <ModuleCard data={data} />)}
            </div>
        </div>

    )
}

export default MainPage