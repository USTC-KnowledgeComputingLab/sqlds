import {
    DataTypes,
    Model,
    Sequelize,
    type CreationOptional,
    type InferAttributes,
    type InferCreationAttributes,
    type ModelStatic,
} from "sequelize";

class Fact extends Model<InferAttributes<Fact>, InferCreationAttributes<Fact>> {
    declare id: CreationOptional<number>;
    declare data: string;
}

class Idea extends Model<InferAttributes<Idea>, InferCreationAttributes<Idea>> {
    declare id: CreationOptional<number>;
    declare data: string;
}

export { Fact, Idea };

export async function initializeDatabase(addr: string): Promise<Sequelize> {
    const sequelize = new Sequelize(addr, { logging: false });

    Fact.init(
        {
            id: { type: DataTypes.INTEGER, primaryKey: true, autoIncrement: true },
            data: { type: DataTypes.TEXT, unique: true, allowNull: false },
        },
        { sequelize, tableName: "facts", timestamps: false },
    );

    Idea.init(
        {
            id: { type: DataTypes.INTEGER, primaryKey: true, autoIncrement: true },
            data: { type: DataTypes.TEXT, unique: true, allowNull: false },
        },
        { sequelize, tableName: "ideas", timestamps: false },
    );

    await sequelize.sync();
    return sequelize;
}

export async function insertOrIgnore(model: typeof Fact | typeof Idea, data: string): Promise<void> {
    await model.bulkCreate([{ data }], {
        ignoreDuplicates: true,
    });
}
