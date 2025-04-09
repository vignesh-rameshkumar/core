import bgImage from '../Assets/background.png';
import ModuleCard from './ModuleCard';
import UserCard from './UserCard';
import EmployeeSearchDrawer from './EmployeeSearchDrawer';
import { useEffect, useState } from 'react';
import { getModules } from '../Utils/helpers';

const MainPage = () => {
    const [modules, setModules] = useState<any>([])

    useEffect(() => {
        const fetchModules = async () => {
            const tempData = await getModules();
            setModules(tempData)
        }
        fetchModules()
    }, [])

    return (
        <div className="bg-cover bg-center h-screen w-full !overflow-hidden"
            style={{ backgroundImage: `url(${bgImage})` }}
        >
            <EmployeeSearchDrawer />
            <div className='grid grid-cols-1 md:grid-cols-3 gap-6 h-full overflow-y-auto py-25 px-5 sm:px-15'>
                <UserCard />
                {modules?.map((data: any) => <ModuleCard data={data} />)}
            </div>
        </div>

    )
}

export default MainPage